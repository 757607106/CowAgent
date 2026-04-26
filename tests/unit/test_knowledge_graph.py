from pathlib import Path

from agent.knowledge.service import KnowledgeService


def _write_page(workspace: Path, rel_path: str, content: str) -> None:
    page_path = workspace / "knowledge" / rel_path
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(content, encoding="utf-8")


def _link_pairs(graph: dict) -> set[tuple[str, str]]:
    return {tuple(sorted([link["source"], link["target"]])) for link in graph["links"]}


def test_build_graph_preserves_explicit_markdown_links(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_page(
        workspace,
        "concepts/alpha.md",
        "# Alpha\n\nSee [Beta](beta.md) for the related implementation notes.",
    )
    _write_page(workspace, "concepts/beta.md", "# Beta\n\nImplementation notes.")

    graph = KnowledgeService(str(workspace), enabled=True).build_graph()

    assert _link_pairs(graph) == {("concepts/alpha.md", "concepts/beta.md")}
    assert graph["links"] == [{"source": "concepts/alpha.md", "target": "concepts/beta.md"}]


def test_build_graph_does_not_infer_links_from_title_reference(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_page(
        workspace,
        "concepts/langchain-rag.md",
        "# LangChain RAG 集成与优化\n\n向量检索、重排序和召回优化。",
    )
    _write_page(
        workspace,
        "concepts/document-parsing.md",
        "# 文档解析方案对比与选型\n\n落地时需要结合 LangChain RAG 集成与优化 处理召回链路。",
    )

    graph = KnowledgeService(str(workspace), enabled=True).build_graph()

    assert graph["links"] == []


def test_build_graph_does_not_infer_links_from_shared_knowledge_terms(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_page(
        workspace,
        "concepts/deep-agent.md",
        "# 深度分析智能体\n\n深度分析任务需要拆解目标、收集数据并生成报告。",
    )
    _write_page(
        workspace,
        "concepts/document-parser.md",
        "# 文档解析方案\n\n文档解析用于深度分析任务，负责数据提取、切分和报告素材准备。",
    )

    graph = KnowledgeService(str(workspace), enabled=True).build_graph()

    assert graph["links"] == []
