# -*- coding: utf-8 -*-
import re

from core.llm_client import complete
from core.schemas import CampaignRequest, Influencer, OutreachBundle, OutreachLetter, ScoreBreakdown, SemanticMatchEvidence
from core.translator import translate_campaign_for_api, translate_to_english


class OutreachGenerator:
    """根据 Campaign 与红人生成中英双语合作邀约信。"""

    def generate(
        self,
        campaign: CampaignRequest,
        influencer: Influencer,
        breakdown: ScoreBreakdown | None = None,
        semantic: SemanticMatchEvidence | None = None,
    ) -> OutreachBundle:
        match_hints = self._match_hints(campaign, influencer, breakdown, semantic)
        english = translate_campaign_for_api(campaign)
        zh_prompt = self._build_prompt(campaign, influencer, match_hints, language="zh", breakdown=breakdown, semantic=semantic)
        en_hints = self._match_hints_en(campaign, influencer, breakdown, english, semantic)
        en_prompt = self._build_prompt(
            campaign,
            influencer,
            en_hints,
            language="en",
            english_campaign=english,
            breakdown=breakdown,
            semantic=semantic,
        )

        zh_text = complete(zh_prompt, temperature=0.55, max_tokens=900)
        en_text = complete(en_prompt, temperature=0.55, max_tokens=900)

        if zh_text and en_text:
            zh_letter = self._parse_letter(zh_text, campaign, influencer, match_hints, language="zh")
            en_letter = self._parse_letter(
                en_text,
                campaign,
                influencer,
                en_hints,
                language="en",
                english_campaign=english,
            )
            if self._validate_language(zh_letter, "zh") and self._validate_language(en_letter, "en"):
                return OutreachBundle(zh=zh_letter, en=en_letter)

        return OutreachBundle(
            zh=self._generate_mock_letter(campaign, influencer, match_hints, language="zh"),
            en=self._generate_mock_letter(
                campaign,
                influencer,
                en_hints,
                language="en",
                english_campaign=english,
            ),
        )

    @staticmethod
    def _match_hints(
        campaign: CampaignRequest,
        influencer: Influencer,
        breakdown: ScoreBreakdown | None,
        semantic: SemanticMatchEvidence | None = None,
    ) -> list[str]:
        hints: list[str] = []
        if breakdown and breakdown.semantic_match >= 15 and semantic and semantic.matched_topics:
            display = ScoreBreakdown.semantic_display_score(semantic.similarity)
            hints.append(f"语义匹配 {display}/30，内容主题涉及{'、'.join(semantic.matched_topics[:3])}")
        if breakdown and breakdown.category_match >= 18:
            hints.append(f"内容类别与 {campaign.product_category} 高度相关")
        if breakdown and breakdown.audience_size_fit >= 10:
            hints.append(
                f"粉丝量 {influencer.followers:,} 符合目标区间 "
                f"{campaign.min_followers:,}–{campaign.max_followers:,}"
            )
        if influencer.country and influencer.country.upper() == campaign.target_country.upper():
            hints.append(f"国家/地区与目标市场 {campaign.target_country} 一致")
        if influencer.total_posts is not None and influencer.total_posts >= 100:
            hints.append(f"已发布 {influencer.total_posts} 个作品，内容积累丰富")
        if influencer.description:
            snippet = influencer.description.strip().split("\n")[0][:80]
            if snippet:
                hints.append(f"频道定位：{snippet}")
        return hints[:4]

    @staticmethod
    def _match_hints_en(
        campaign: CampaignRequest,
        influencer: Influencer,
        breakdown: ScoreBreakdown | None,
        english: dict[str, str],
        semantic: SemanticMatchEvidence | None = None,
    ) -> list[str]:
        hints: list[str] = []
        if breakdown and breakdown.semantic_match >= 15 and semantic and semantic.matched_topics:
            display = ScoreBreakdown.semantic_display_score(semantic.similarity)
            hints.append(
                f"Semantic match {display}/30 with topics: {', '.join(semantic.matched_topics[:3])}"
            )
        if breakdown and breakdown.category_match >= 18:
            hints.append(f"Content niche aligns with {english['product_category']}")
        if breakdown and breakdown.audience_size_fit >= 10:
            hints.append(
                f"Follower count {influencer.followers:,} fits the target range "
                f"{campaign.min_followers:,}-{campaign.max_followers:,}"
            )
        if influencer.country and influencer.country.upper() == campaign.target_country.upper():
            hints.append(f"Creator country matches target market {campaign.target_country}")
        if influencer.total_posts is not None and influencer.total_posts >= 100:
            hints.append(f"Published {influencer.total_posts} videos with consistent activity")
        if influencer.description:
            snippet = influencer.description.strip().split("\n")[0][:80]
            if snippet:
                hints.append(f"Channel focus: {snippet}")
        return hints[:4]

    @staticmethod
    def _build_prompt(
        campaign: CampaignRequest,
        influencer: Influencer,
        match_hints: list[str],
        *,
        language: str,
        english_campaign: dict[str, str] | None = None,
        breakdown: ScoreBreakdown | None = None,
        semantic: SemanticMatchEvidence | None = None,
    ) -> str:
        hints_text = "；".join(match_hints) if match_hints else "频道风格与产品定位契合"
        display_name = influencer.name or influencer.username
        score_line = ""
        score_line_en = ""
        if breakdown:
            display = (
                ScoreBreakdown.semantic_display_score(semantic.similarity)
                if semantic
                else breakdown.semantic_match
            )
            score_line = f"匹配总分 {breakdown.total_score} 分（语义 {display}/30）。"
            score_line_en = f"Total match score {breakdown.total_score} (semantic {display}/30)."

        if language == "zh":
            return (
                "请为品牌方撰写一封中文红人合作邀约邮件。\n"
                "要求：高情商、商务合作风格、非群发感；结合红人频道信息与匹配原因；"
                "正文必须全中文，不得出现任何英文字母或英文句子；"
                "输出格式严格为两行：\n"
                "Subject: ...\n"
                "Body: ...\n\n"
                f"品牌产品：{campaign.product_name}\n"
                f"产品类别：{campaign.product_category}\n"
                f"产品描述：{campaign.product_description}\n"
                f"Campaign 预算：USD {campaign.campaign_budget:,.0f}\n"
                f"红人：{display_name}（@{influencer.username}，{influencer.platform.value}）\n"
                f"红人类别：{influencer.category}\n"
                f"匹配原因：{hints_text}\n"
                f"{score_line}"
            )

        return (
            "Write a professional influencer partnership outreach email in English.\n"
            "Requirements: warm, business-appropriate, personalized; reference channel info and match reasons; "
            "the entire email must be in English with no Chinese characters.\n"
            "Output format strictly two lines:\n"
            "Subject: ...\n"
            "Body: ...\n\n"
            f"Brand product: {english_campaign['product_name'] if english_campaign else campaign.product_name}\n"
            f"Category: {english_campaign['product_category'] if english_campaign else campaign.product_category}\n"
            f"Description: {(english_campaign or translate_campaign_for_api(campaign))['product_description']}\n"
            f"Campaign budget: USD {campaign.campaign_budget:,.0f}\n"
            f"Influencer: {display_name} (@{influencer.username} on {influencer.platform.value})\n"
            f"Influencer niche: {influencer.category}\n"
            f"Match reasons: {hints_text}\n"
            f"{score_line_en}"
        )

    @staticmethod
    def _parse_letter(
        text: str,
        campaign: CampaignRequest,
        influencer: Influencer,
        match_hints: list[str],
        *,
        language: str,
        english_campaign: dict[str, str] | None = None,
    ) -> OutreachLetter:
        subject = ""
        body_lines: list[str] = []
        mode = None
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if mode == "body":
                    body_lines.append("")
                continue
            lower = stripped.lower()
            if lower.startswith("subject:"):
                subject = stripped.split(":", 1)[1].strip()
                mode = "subject"
                continue
            if lower.startswith("body:"):
                body_lines.append(stripped.split(":", 1)[1].strip())
                mode = "body"
                continue
            if mode == "body":
                body_lines.append(stripped)

        if not subject or not body_lines:
            return OutreachGenerator._generate_mock_letter(
                campaign,
                influencer,
                match_hints,
                language=language,
                english_campaign=english_campaign,
            )

        return OutreachLetter(subject=subject, body="\n".join(body_lines).strip())

    @staticmethod
    def _validate_language(letter: OutreachLetter, language: str) -> bool:
        content = f"{letter.subject}\n{letter.body}"
        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", content))
        if language == "zh":
            return has_chinese
        return not has_chinese

    @staticmethod
    def _generate_mock_letter(
        campaign: CampaignRequest,
        influencer: Influencer,
        match_hints: list[str],
        *,
        language: str,
        english_campaign: dict[str, str] | None = None,
    ) -> OutreachLetter:
        display_name = influencer.name or influencer.username
        content_hook = influencer.description.split("\n")[0][:60] if influencer.description else influencer.category
        english = english_campaign or translate_campaign_for_api(campaign)
        hint_line = "、".join(match_hints[:2]) if match_hints else f"与 {campaign.product_category} 内容方向契合"
        hint_line_en = ", ".join(match_hints[:2]) if match_hints else f"aligned with {english['product_category']}"

        if language == "zh":
            subject = f"品牌合作邀请｜{campaign.product_name} × @{influencer.username}"
            body = (
                f"您好 {display_name}，\n\n"
                f"我们长期关注您在 {influencer.platform.value} 上的内容创作，"
                f"尤其欣赏您在「{influencer.category}」领域的真实表达。"
                f"我们注意到您的频道（{content_hook}…）与我们的合作方向高度契合：{hint_line}。\n\n"
                f"我们即将推广 {campaign.product_name}（{campaign.product_category}）。"
                f"{campaign.product_description.strip()}\n\n"
                f"基于以上匹配原因，诚挚邀请您探讨一次真实产品体验合作。"
                f"本次推广预算约为 {campaign.campaign_budget:,.0f} 美元，"
                f"期待与您沟通内容形式、发布节奏及合作细节。\n\n"
                f"若您有兴趣，欢迎回复此邮件，我们将为您寄送产品样品并提供详细合作说明。\n\n"
                f"期待与您携手，\n"
                f"{campaign.product_name} 品牌团队"
            )
            return OutreachLetter(subject=subject, body=body)

        subject = f"Partnership Invitation: {english['product_name']} x @{influencer.username}"
        body = (
            f"Dear {display_name},\n\n"
            f"We have been following your work on {influencer.platform.value}, "
            f"particularly your authentic content in the {influencer.category} space. "
            f"Your channel focus ({content_hook}...) aligns well with our campaign goals: {hint_line_en}.\n\n"
            f"We are preparing a launch for {english['product_name']}, a {english['product_category']} product. "
            f"{english['product_description'].strip()}\n\n"
            f"Given this strong fit, we would love to explore a genuine product experience collaboration with you. "
            f"Our campaign budget is approximately USD {campaign.campaign_budget:,.0f}, "
            f"and we would welcome a conversation about content format, timeline, and partnership terms.\n\n"
            f"If you are interested, please reply to this email and we will share product samples "
            f"and a detailed campaign brief at your convenience.\n\n"
            f"Warm regards,\n"
            f"The {english['product_name']} Team"
        )
        return OutreachLetter(subject=subject, body=body)
