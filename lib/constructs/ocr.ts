import * as cdk from "aws-cdk-lib";
import {
  ScalableTarget,
  ServiceNamespace,
  TargetTrackingScalingPolicy,
  StepScalingPolicy,
  PredefinedMetric,
  AdjustmentType,
  MetricAggregationType,
} from "aws-cdk-lib/aws-applicationautoscaling";
import { Metric } from "aws-cdk-lib/aws-cloudwatch";
import { DockerImageAsset, Platform } from "aws-cdk-lib/aws-ecr-assets";
import {
  ManagedPolicy,
  PolicyStatement,
  Role,
  ServicePrincipal,
} from "aws-cdk-lib/aws-iam";
import {
  CfnModel,
  CfnEndpointConfig,
  CfnEndpoint,
  CfnInferenceComponent,
} from "aws-cdk-lib/aws-sagemaker";
import { Construct } from "constructs";
import * as path from "path";

export interface OcrProps {
  baseName?: string;
  ocrEngine?: "paddle";
  instanceType?: string;
  environment?: Record<string, string>;
  enableZeroScale?: boolean;
  scaleInCooldownSeconds?: number;
}

export class Ocr extends Construct {
  public readonly endpointName: string;
  public readonly inferenceComponentName: string;
  public readonly sagemakerRoleArn: string;

  constructor(scope: Construct, id: string, props: OcrProps = {}) {
    super(scope, id);

    // デフォルト値の設定
    const baseName = props.baseName || "ocr";
    const instanceType = props.instanceType || "ml.g5.2xlarge";
    const ocrEngine = props.ocrEngine || "paddle";

    // PaddleOCRのコンテナパス
    const containerPath = path.join(
      __dirname,
      "../../ocr-containers/paddle-ocr"
    );

    const variantName = "AllTraffic";
    this.inferenceComponentName = `${baseName}-inference-component`;

    // PaddleOCR用のデフォルト環境変数
    const defaultEnv = {
      USE_GPU: "true",
      CUDA_VISIBLE_DEVICES: "0",
    };

    // デフォルトと指定された環境変数をマージ
    const environment = {
      ...defaultEnv,
      ...(props.environment || {}),
    };

    // SageMaker用のIAMロール
    const sagemakerRole = new Role(this, "SageMakerExecutionRole", {
      assumedBy: new ServicePrincipal("sagemaker.amazonaws.com"),
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName("AmazonSageMakerFullAccess"),
        ManagedPolicy.fromAwsManagedPolicyName("AmazonS3ReadOnlyAccess"),
      ],
    });

    // CloudWatch Logsの許可を追加
    sagemakerRole.addToPolicy(
      new PolicyStatement({
        actions: [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ],
        resources: [
          `arn:aws:logs:${cdk.Stack.of(this).region}:${
            cdk.Stack.of(this).account
          }:log-group:/aws/sagemaker/*`,
        ],
      })
    );

    // ECRへの認証許可を追加
    sagemakerRole.addToPolicy(
      new PolicyStatement({
        actions: ["ecr:GetAuthorizationToken"],
        resources: ["*"],
      })
    );

    // コンテナイメージのビルドとECRへのプッシュ
    const dockerImage = new DockerImageAsset(this, "OcrDockerImage", {
      directory: containerPath,
      buildArgs: {},
      exclude: [".git", "node_modules"],
      platform: Platform.LINUX_AMD64,
    });

    const model = new CfnModel(this, "OcrModel", {
      executionRoleArn: sagemakerRole.roleArn,
      primaryContainer: {
        image: dockerImage.imageUri,
        environment: environment,
      },
    });

    const endpointConfig = new CfnEndpointConfig(this, "OcrEndpointConfig", {
      executionRoleArn: sagemakerRole.roleArn,
      productionVariants: [
        {
          variantName: variantName,
          instanceType: instanceType,
          initialInstanceCount: 1,
          routingConfig: {
            routingStrategy: "LEAST_OUTSTANDING_REQUESTS",
          },
          containerStartupHealthCheckTimeoutInSeconds: 600,
          modelDataDownloadTimeoutInSeconds: 600,
        },
      ],
    });

    const endpoint = new CfnEndpoint(this, "OcrEndpoint", {
      endpointConfigName: endpointConfig.attrEndpointConfigName,
    });

    this.endpointName = endpoint.attrEndpointName;

    endpoint.addDependency(endpointConfig);

    const inferenceComponent = new CfnInferenceComponent(
      this,
      "OcrInferenceComponent",
      {
        inferenceComponentName: this.inferenceComponentName,
        endpointName: endpoint.attrEndpointName,
        variantName: variantName,
        specification: {
          modelName: model.attrModelName,
          computeResourceRequirements: {
            numberOfAcceleratorDevicesRequired: 1,
            numberOfCpuCoresRequired: 1,
            minMemoryRequiredInMb: 4096,
          },
        },
        runtimeConfig: {
          copyCount: 1,
        },
      }
    );

    inferenceComponent.addDependency(endpoint);
    inferenceComponent.addDependency(model);

    // Auto Scaling設定（ゼロスケール）
    if (props.enableZeroScale) {
      const resourceId = `inference-component/${this.inferenceComponentName}`;

      const scalableTarget = new ScalableTarget(this, "ScalableTarget", {
        serviceNamespace: ServiceNamespace.SAGEMAKER,
        scalableDimension: "sagemaker:inference-component:DesiredCopyCount",
        resourceId: resourceId,
        minCapacity: 0,
        maxCapacity: 1,
      });

      scalableTarget.node.addDependency(inferenceComponent);

      // ターゲットトラッキングポリシー（スケールイン用）
      new TargetTrackingScalingPolicy(this, "TargetTrackingPolicy", {
        scalingTarget: scalableTarget,
        targetValue: 1,
        predefinedMetric:
          PredefinedMetric.SAGEMAKER_INFERENCE_COMPONENT_INVOCATIONS_PER_COPY,
        scaleInCooldown: cdk.Duration.seconds(props.scaleInCooldownSeconds || 3600),
        scaleOutCooldown: cdk.Duration.seconds(60),
      });

      // ステップスケーリングポリシー（スケールアウト用）
      const noCapacityMetric = new Metric({
        namespace: "AWS/SageMaker",
        metricName: "NoCapacityInvocationFailures",
        dimensionsMap: {
          InferenceComponentName: this.inferenceComponentName,
        },
        statistic: "Maximum",
        period: cdk.Duration.seconds(60),
      });

      new StepScalingPolicy(this, "StepScalingPolicy", {
        scalingTarget: scalableTarget,
        adjustmentType: AdjustmentType.CHANGE_IN_CAPACITY,
        metricAggregationType: MetricAggregationType.MAXIMUM,
        cooldown: cdk.Duration.seconds(60),
        scalingSteps: [
          { change: 1, lower: 0 },
          { change: 0, upper: -1 },
        ],
        metric: noCapacityMetric,
      });
    }

    this.sagemakerRoleArn = sagemakerRole.roleArn;

    new cdk.CfnOutput(this, "DockerImageUri", {
      value: dockerImage.imageUri,
      description: "ECRのDockerイメージURI",
    });

    new cdk.CfnOutput(this, "SageMakerEndpointName", {
      value: this.endpointName,
      description: "SageMakerエンドポイント名",
    });

    new cdk.CfnOutput(this, "SageMakerInferenceComponentName", {
      value: this.inferenceComponentName,
      description: "SageMaker推論コンポーネント名",
    });

    new cdk.CfnOutput(this, "SageMakerRoleArn", {
      value: this.sagemakerRoleArn,
      description: "SageMaker実行ロールARN",
    });
  }
}
