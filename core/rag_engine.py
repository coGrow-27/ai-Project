# -*- coding: utf-8 -*-
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from config.settings import settings
from core.llm_client import complete
from core.runtime import is_llm_enabled, is_rag_mock

try:
    from llama_index.core import Document, Settings, VectorStoreIndex
    from llama_index.core.llms import CompletionResponse, CustomLLM, LLMMetadata
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
except ImportError:  # pragma: no cover
    Document = None
    VectorStoreIndex = None
    Settings = None
    HuggingFaceEmbedding = None
    CompletionResponse = None
    CustomLLM = object
    LLMMetadata = None


logger = logging.getLogger("rag_engine")


class GatewayLLM(CustomLLM):
    """LlamaIndex 适配层，底层统一走 core.llm_client。"""

    model_name: str = "gateway"

    @property
    def metadata(self) -> Any:
        if LLMMetadata is None:
            return {"model_name": self.model_name, "is_chat_model": True}
        return LLMMetadata(model_name=self.model_name, is_chat_model=True)

    def complete(self, prompt: str, **kwargs: Any) -> Any:
        text = complete(prompt, temperature=0.35, max_tokens=1200)
        if not text:
            raise RuntimeError("LLM 不可用或调用失败。")
        return CompletionResponse(text=text) if CompletionResponse is not None else text

    def stream_complete(self, prompt: str, **kwargs: Any) -> Iterable[Any]:
        response = self.complete(prompt, **kwargs)
        text = response.text if hasattr(response, "text") else str(response)
        if CompletionResponse is not None:
            yield CompletionResponse(text=text, delta=text)
        else:
            yield text


@dataclass
class RetrievedInfluencer:
    influencer: Dict[str, Any]
    score: int
    evidence: List[str]


class InfluencerRagEngine:
    def __init__(self, use_mock: Optional[bool] = None):
        self.use_mock = is_rag_mock() if use_mock is None else use_mock
        self.index = None
        self.documents: List[Dict[str, Any]] = []
        self.llm = None
        self.embed_model = None

        if not self.use_mock:
            if VectorStoreIndex is None or Document is None or HuggingFaceEmbedding is None:
                raise RuntimeError("USE_MOCK=False 时需要安装 LlamaIndex 和 HuggingFace 相关依赖。")
            if is_llm_enabled():
                self.llm = GatewayLLM(model_name=settings.LLM_PROVIDER)
                Settings.llm = self.llm
            self.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
            Settings.embed_model = self.embed_model

    def build_index(self, raw_influencers: List[Dict[str, Any]]) -> None:
        if not raw_influencers:
            raise ValueError("红人数据为空，无法构建 RAG 索引。")

        self.documents = raw_influencers
        if self.use_mock:
            self.index = "mock-keyword-index"
            logger.info("已构建 Mock 关键词索引，共 %s 位红人。", len(raw_influencers))
            return

        docs = [
            Document(
                text=self._format_influencer_document(item),
                metadata={
                    "influencer_id": item.get("influencer_id"),
                    "username": item.get("username"),
                    "region": item.get("region"),
                    "follower_count": item.get("follower_count"),
                    "engagement_rate": item.get("engagement_rate"),
                },
            )
            for item in raw_influencers
        ]
        self.index = VectorStoreIndex.from_documents(docs)
        logger.info("已构建向量索引，共 %s 位红人。", len(raw_influencers))

    def build_campaign_index(self, raw_influencers: List[Dict[str, Any]]) -> None:
        """Campaign 主链路：使用 document_text 字段构建临时索引。"""
        if not raw_influencers:
            raise ValueError("Campaign 候选为空，无法构建语义索引。")

        self.documents = raw_influencers
        if self.use_mock:
            self.index = "mock-keyword-index"
            return

        docs = [
            Document(
                text=item.get("document_text") or self._format_influencer_document(item),
                metadata={
                    "influencer_id": item.get("influencer_id"),
                    "username": item.get("username"),
                    "region": item.get("region"),
                },
            )
            for item in raw_influencers
        ]
        self.index = VectorStoreIndex.from_documents(docs)

    def close_campaign_index(self) -> None:
        self.index = None
        self.documents = []

    def retrieve_campaign(self, query: str, top_k: int = 10) -> Dict[str, Dict[str, Any]]:
        """返回 influencer_id -> {score, evidence} 映射，供 Semantic Match 使用。"""
        if not self.documents:
            return {}
        if self.use_mock or self.index == "mock-keyword-index":
            return self._retrieve_campaign_mock(query, top_k=top_k)
        return self._retrieve_campaign_vector(query, top_k=top_k)

    def _retrieve_campaign_mock(self, query: str, *, top_k: int) -> Dict[str, Dict[str, Any]]:
        terms = self._tokenize(query)
        ranked: Dict[str, Dict[str, Any]] = {}
        for influencer in self.documents:
            influencer_id = str(influencer.get("influencer_id", ""))
            if not influencer_id:
                continue
            text = influencer.get("document_text") or self._format_influencer_document(influencer)
            text_lower = text.lower()
            evidence = self._collect_campaign_evidence(text, terms)
            score = float(sum(text_lower.count(term) for term in terms) + len(evidence) * 2)
            if score > 0:
                ranked[influencer_id] = {"score": score, "evidence": evidence[:3]}
        if not ranked:
            for influencer in self.documents[:top_k]:
                influencer_id = str(influencer.get("influencer_id", ""))
                text = influencer.get("document_text") or self._format_influencer_document(influencer)
                ranked[influencer_id] = {"score": 0.1, "evidence": [text.splitlines()[0][:120]]}
        return ranked

    def _retrieve_campaign_vector(self, query: str, *, top_k: int) -> Dict[str, Dict[str, Any]]:
        if self.index is None:
            return self._retrieve_campaign_mock(query, top_k=top_k)
        retriever = self.index.as_retriever(similarity_top_k=min(top_k, len(self.documents)))
        nodes = retriever.retrieve(query)
        ranked: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            influencer_id = str(node.metadata.get("influencer_id", ""))
            if not influencer_id:
                continue
            score = float(getattr(node, "score", 0.0) or 0.0)
            snippet = node.get_content()[:180]
            evidence = ranked.get(influencer_id, {}).get("evidence", [])
            evidence.append(snippet)
            ranked[influencer_id] = {"score": max(score, ranked.get(influencer_id, {}).get("score", 0.0)), "evidence": evidence[:3]}
        return ranked

    @staticmethod
    def _collect_campaign_evidence(document_text: str, terms: List[str]) -> List[str]:
        evidence: List[str] = []
        for line in document_text.splitlines():
            lower = line.lower()
            if any(term in lower for term in terms):
                evidence.append(line.strip())
        return evidence

    def query(self, requirement: str) -> str:
        if self.index is None:
            raise ValueError("RAG 索引为空，请先调用 build_index。")
        if not requirement or not requirement.strip():
            raise ValueError("需求不能为空。")

        if self.use_mock:
            matches = self.retrieve(requirement, top_k=3)
            return self._generate_mock_pitch(requirement, matches)

        if is_llm_enabled() and self.llm is not None:
            try:
                engine = self.index.as_query_engine(streaming=False)
                response = engine.query(self._build_prompt(requirement))
                return str(response)
            except Exception as exc:
                logger.warning("向量 RAG + LLM 失败，回退到检索模板：%s", exc)

        matches = self.retrieve(requirement, top_k=3)
        return self._generate_mock_pitch(requirement, matches)

    def generate_pitch_letter(self, product_desc: str) -> str:
        return self.query(product_desc)

    def retrieve(self, requirement: str, top_k: int = 3) -> List[RetrievedInfluencer]:
        terms = self._tokenize(requirement)
        ranked: List[RetrievedInfluencer] = []
        for influencer in self.documents:
            text = self._format_influencer_document(influencer)
            text_lower = text.lower()
            evidence = self._collect_evidence(influencer, terms)
            score = sum(text_lower.count(term) for term in terms) + len(evidence) * 2
            score += int(float(influencer.get("engagement_rate", 0)) * 100)
            if score > 0:
                ranked.append(RetrievedInfluencer(influencer=influencer, score=score, evidence=evidence[:3]))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        text_lower = text.lower()
        tokens = re.findall(r"[a-zA-Z0-9]+", text_lower)
        stop_words = {"the", "and", "for", "with", "this", "that", "need", "from", "your", "into"}
        keyword_map = {
            "猫": ["cat", "cats"],
            "狗": ["dog", "dogs"],
            "宠物": ["pet"],
            "去毛": ["hair", "remover", "brush"],
            "梳": ["brush", "grooming"],
            "清理": ["clean", "cleaning"],
            "一键": ["self", "cleaning"],
            "温和": ["gentle", "soft"],
            "不伤": ["skin", "scratch"],
            "美国": ["us"],
            "英国": ["uk"],
            "红人": ["influencer", "reviewer"],
        }
        for keyword, mapped_terms in keyword_map.items():
            if keyword in text_lower:
                tokens.extend(mapped_terms)

        filtered = [token for token in tokens if len(token) > 2 and token not in stop_words]
        return list(dict.fromkeys(filtered))

    @staticmethod
    def _format_influencer_document(influencer: Dict[str, Any]) -> str:
        pieces = [
            f"用户名：{influencer.get('username', '')}",
            f"地区：{influencer.get('region', '')}",
            f"粉丝数：{influencer.get('follower_count', '')}",
            f"互动率：{influencer.get('engagement_rate', '')}",
            f"简介：{influencer.get('bio', '')}",
            f"风格标签：{', '.join(influencer.get('style_tags', []))}",
        ]
        for video in influencer.get("recent_videos", []):
            pieces.append(f"视频标题：{video.get('video_title', '')}")
            pieces.append(f"视频脚本：{video.get('script_text', '')}")
            for comment in video.get("comments", []):
                pieces.append(f"评论：{comment}")
        return "\n".join(pieces)

    def _collect_evidence(self, influencer: Dict[str, Any], terms: List[str]) -> List[str]:
        evidence: List[str] = []
        for video in influencer.get("recent_videos", []):
            candidates = [video.get("video_title", ""), video.get("script_text", ""), *video.get("comments", [])]
            for candidate in candidates:
                candidate_text = str(candidate)
                lower = candidate_text.lower()
                if any(term in lower for term in terms):
                    evidence.append(candidate_text)
        return evidence

    @staticmethod
    def _build_prompt(requirement: str) -> str:
        return (
            "你是一名红人营销策略顾问。请根据检索到的红人证据匹配商家需求，"
            "说明匹配理由，并写一封简洁的开发信。\n\n"
            f"商家需求：\n{requirement}"
        )

    @staticmethod
    def _generate_mock_pitch(requirement: str, matches: List[RetrievedInfluencer]) -> str:
        if not matches:
            return "当前需求未找到合适的红人。"

        lines = [
            "红人匹配结果",
            f"商家需求：{requirement.strip()}",
            "",
        ]
        for index, match in enumerate(matches, start=1):
            influencer = match.influencer
            lines.extend(
                [
                    f"{index}. @{influencer.get('username')} - 匹配分 {match.score}",
                    f"   地区：{influencer.get('region')} | 粉丝数：{influencer.get('follower_count')} | 互动率：{influencer.get('engagement_rate')}",
                    "   理由：其内容和评论区体现了宠物梳毛、去浮毛、工具体验等相关痛点。",
                ]
            )
            if match.evidence:
                lines.append(f"   证据：{match.evidence[0]}")
        best = matches[0].influencer
        lines.extend(
            [
                "",
                "开发信草稿：",
                f"Hi {best.get('username')}，我们注意到你的受众很关注实用型宠物梳毛工具。"
                "我们正在推出一款主打温和梳毛、一键清理和舒适握持的宠物梳，"
                "你的近期内容非常适合做一次真实、细致的产品体验分享。",
            ]
        )
        return "\n".join(lines)
