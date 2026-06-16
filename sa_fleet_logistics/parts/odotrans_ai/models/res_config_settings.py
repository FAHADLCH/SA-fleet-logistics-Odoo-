# -*- coding: utf-8 -*-
"""AI provider configuration exposed in Settings."""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    odotrans_ai_provider = fields.Selection(
        [
            ("heuristic", "Built-in (offline, no key)"),
            ("openai", "OpenAI"),
            ("azure_openai", "Azure OpenAI"),
        ],
        string="AI Provider",
        default="heuristic",
        config_parameter="odotrans.ai.provider",
    )

    # OpenAI
    odotrans_openai_api_key = fields.Char(
        string="OpenAI API Key", config_parameter="odotrans.ai.openai.api_key",
    )
    odotrans_openai_model = fields.Char(
        string="OpenAI Model", config_parameter="odotrans.ai.openai.model",
    )

    # Azure OpenAI
    odotrans_azure_endpoint = fields.Char(
        string="Azure Endpoint", config_parameter="odotrans.ai.azure_openai.endpoint",
    )
    odotrans_azure_api_key = fields.Char(
        string="Azure API Key", config_parameter="odotrans.ai.azure_openai.api_key",
    )
    odotrans_azure_deployment = fields.Char(
        string="Azure Deployment", config_parameter="odotrans.ai.azure_openai.deployment",
    )

    # Feature toggles
    odotrans_ai_enable_eta = fields.Boolean(
        string="Predictive ETA", default=True, config_parameter="odotrans.ai.enable_eta",
    )
    odotrans_ai_enable_risk = fields.Boolean(
        string="Delay Risk Scoring", default=True, config_parameter="odotrans.ai.enable_risk",
    )
    odotrans_ai_enable_pricing = fields.Boolean(
        string="Dynamic Pricing", default=True, config_parameter="odotrans.ai.enable_pricing",
    )

    @api.model
    def odotrans_ai_smoke_test(self):
        return self.env["odotrans.ai"].assist("show me late shipments")
