import * as cdk from "aws-cdk-lib";
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
  ocrEngine?: "paddle" | "deepseek";
  instanceType?: string;
  environment?: Record<string, string>;
}

export class Ocr extends Construct {
  public readonly endpointName: string;
  public readonly inferenceComponentName: string;
  public readonly sagemakerRoleArn: string;

  constructor(scope: Construct, id: string, props: OcrProps = {}) {
    super(scope, id);

    // デフォルト値の設定
    const baseName = props.baseName || "ocr";
    const ocrEngine = props.ocrEngine || "paddle";
    const instanceType = props.instanceType || (ocrEngine === "paddle" ? "ml.g5.2xlarge" : "ml.g5.4xlarge");

    // OCRエンジンに応じたコンテナパス
    const containerMap = {
      paddle: "paddle-ocr", 
      deepseek: "deepseek-ocr"
    };
    const containerPath = path.join(
      __dirname,
      `../../ocr-containers/${containerMap[ocrEngine] || ocrEngine}`
    );

    const variantName = "AllTraffic";
    this.inferenceComponentName = `${baseName}-inference-component`;

    // OCRエンジン用のデフォルト環境変数
    let defaultEnv: Record<string, string> = {
      USE_GPU: "true",
      CUDA_VISIBLE_DEVICES: "0",
      OCR_ENGINE: ocrEngine,
    };

    // DeepSeek OCR用の追加環境変数
    if (ocrEngine === "deepseek") {
      defaultEnv = {
        ...defaultEnv,
        CROP_MODE: 'true',
        MODEL_PATH: 'deepseek-ai/DeepSeek-OCR',
        TORCH_CUDA_ARCH_LIST: '8.6',
        NVIDIA_VISIBLE_DEVICES: 'all',
        NVIDIA_DRIVER_CAPABILITIES: 'compute,utility',
      };
    }

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
      modelName: containerMap[ocrEngine],
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

    // OCRエンジンに応じたリソース要件
    let cpuCores = 1;
    let memoryMb = 4096;
    let acceleratorDevices = 1;
    
    if (ocrEngine === "deepseek") {
      cpuCores = 8;
      memoryMb = 42768;
      acceleratorDevices = 1;
    }

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
            numberOfAcceleratorDevicesRequired: acceleratorDevices,
            numberOfCpuCoresRequired: cpuCores,
            minMemoryRequiredInMb: memoryMb,
          },
        },
        runtimeConfig: {
          copyCount: 1,
        },
      }
    );

    inferenceComponent.addDependency(endpoint);
    inferenceComponent.addDependency(model);

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
