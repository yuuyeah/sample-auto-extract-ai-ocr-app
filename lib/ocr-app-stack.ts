import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

import { Auth } from "./constructs/auth";
import { Api } from "./constructs/api";
import { Web } from "./constructs/web";
import { Database } from "./constructs/database";
import { Ocr } from "./constructs/ocr";
import { Agent } from "./constructs/agent";

export class OcrAppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // OCR有効フラグを取得（デフォルトはtrue）
    const enableOcr = this.node.tryGetContext("enable_ocr") ?? true;

    // Agent有効フラグを取得（デフォルトはfalse）
    const enableAgent = this.node.tryGetContext("enable_agent") ?? false;
    const enableAgentDemo =
      this.node.tryGetContext("enable_agent_demo") ?? false;

    const auth = new Auth(this, "Auth");

    const database = new Database(this, "Database");

    // OCRが有効な場合のみSageMakerエンドポイントを作成
    let ocrEndpoint = undefined;
    if (enableOcr) {
      const ocr = new Ocr(this, "OcrEndpoint");
      ocrEndpoint = ocr;
    }

    // Agentが有効な場合のみAgentを作成
    let agent = undefined;
    if (enableAgent) {
      agent = new Agent(this, "Agent", {
        region: this.region,
        enableDemo: enableAgentDemo,
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

    new Web(this, "WebConstruct", {
      buildFolder: "/dist",
      userPoolId: auth.userPool.userPoolId,
      userPoolClientId: auth.client.userPoolClientId,
      apiUrl: api.apiEndpoint,
      enableOcr: enableOcr,
    });
  }
}
