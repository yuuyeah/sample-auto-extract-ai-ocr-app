import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

import { Auth } from "./constructs/auth";
import { Api } from "./constructs/api";
import { Web } from "./constructs/web";
import { Database } from "./constructs/database";
import { Ocr } from "./constructs/ocr";
import { Agent } from "./constructs/agent";
import { StepFunctions } from "./constructs/step-functions";

export class OcrAppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // OCR有効フラグを取得（デフォルトはtrue）
    const enableOcr = this.node.tryGetContext("enable_ocr") ?? true;

    // OCRエンジンを取得（デフォルトはpaddle）
    const ocrEngine = this.node.tryGetContext("ocr_engine") ?? "paddle";

    // Agent有効フラグを取得（デフォルトはfalse）
    const enableAgent = this.node.tryGetContext("enable_agent") ?? false;
    const enableAgentDemo =
      this.node.tryGetContext("enable_agent_demo") ?? false;

    const auth = new Auth(this, "Auth");

    const database = new Database(this, "Database");

    // OCRが有効な場合のみSageMakerエンドポイントを作成
    let ocrEndpoint = undefined;
    if (enableOcr) {
      const enableZeroScale =
        this.node.tryGetContext("sagemaker_zero_scale") ?? true;
      const scaleInCooldownSeconds =
        this.node.tryGetContext("sagemaker_scale_in_cooldown_seconds") ?? 3600;

      const ocr = new Ocr(this, "OcrEndpoint", {
        enableZeroScale: enableZeroScale,
        scaleInCooldownSeconds: scaleInCooldownSeconds,
        ocrEngine: ocrEngine as "paddle" | "deepseek" | "yomitoku",
      });
      ocrEndpoint = ocr;
    }

    // Agentが有効な場合のみAgentを作成
    let agent = undefined;
    if (enableAgent) {
      agent = new Agent(this, "Agent", {
        region: this.region,
        enableDemo: enableAgentDemo,
        schemasTable: database.schemasTable,
      });
    }

    const api = new Api(this, "Api", {
      imagesTable: database.imagesTable,
      jobsTable: database.jobsTable,
      schemasTable: database.schemasTable,
      toolsTable: agent?.toolsTable,
      userPoolId: auth.userPool.userPoolId,
      userPoolClientId: auth.client.userPoolClientId,
      enableOcr: enableOcr,
      sagemakerEndpointName: ocrEndpoint?.endpointName,
      sagemakerInferenceComponentName: ocrEndpoint?.inferenceComponentName,
      agentRuntimeArn: agent?.runtimeArn,
    });

    // Step Functions追加
    const stepFunctions = new StepFunctions(this, "StepFunctions", {
      imagesTable: database.imagesTable,
      jobsTable: database.jobsTable,
      schemasTable: database.schemasTable,
      documentBucket: api.documentBucket,
      enableOcr,
      sagemakerEndpointName: ocrEndpoint?.endpointName,
      sagemakerInferenceComponentName: ocrEndpoint?.inferenceComponentName,
    });

    // API LambdaにStep Functions実行権限を付与
    stepFunctions.stateMachine.grantStartExecution(api.handler);

    // 環境変数追加
    api.handler.addEnvironment(
      "STATE_MACHINE_ARN",
      stepFunctions.stateMachine.stateMachineArn
    );

    new Web(this, "WebConstruct", {
      buildFolder: "/dist",
      userPoolId: auth.userPool.userPoolId,
      userPoolClientId: auth.client.userPoolClientId,
      apiUrl: api.apiEndpoint,
      enableOcr: enableOcr,
      enableAgent: enableAgent,
      syncBucketName: api.syncBucket.bucketName,
    });

    // 出力
    new cdk.CfnOutput(this, "StateMachineArn", {
      value: stepFunctions.stateMachine.stateMachineArn,
      description: "OCR Step Functions State Machine ARN",
    });
  }
}
