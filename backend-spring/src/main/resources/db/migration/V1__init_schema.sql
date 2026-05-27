CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

		username VARCHAR(50) NOT NULL UNIQUE,
		email VARCHAR(255) NOT NULL UNIQUE,
		password_hash VARCHAR(255) NOT NULL,

		status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',

		created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE knowledge_bases(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 知识库 ID

    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name VARCHAR(100) NOT NULL,    -- 页面展示名称，例如 Product Docs
    slug VARCHAR(120) NOT NULL,    -- 稳定标识，例如 product-docs
    description TEXT,

    icon VARCHAR(50) NOT NULL DEFAULT 'folder', -- UI 图标，例如 folder, file-text
    color VARCHAR(30) NOT NULL DEFAULT 'blue',  -- UI 主题色，例如 blue, green, purple
    display_order INTEGER NOT NULL DEFAULT 0,   -- UI 排序

	source_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,

    -- 后面可能对知识库删除，隐藏等等，所以先留着； ACTIVE，ARCHIVED，DISABLED
	status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',  -- 是否启用

	last_imported_at TIMESTAMP,       -- 最近一次导入成功时间
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_knowledge_bases_user_slug UNIQUE (user_id, slug),

    CONSTRAINT chk_knowledge_bases_status
        CHECK (status IN ('ACTIVE', 'ARCHIVED', 'DISABLED')),

    CONSTRAINT chk_knowledge_bases_source_count
        CHECK (source_count >= 0),

    CONSTRAINT chk_knowledge_bases_chunk_count
        CHECK (chunk_count >= 0)
);



CREATE TABLE import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    knowledge_base_id UUID NOT NULL
        REFERENCES knowledge_bases(id)
        ON DELETE CASCADE,

    import_type VARCHAR(30) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'PROCESSING',

    total_items INTEGER NOT NULL DEFAULT 0,
    processed_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,

    total_chunks INTEGER NOT NULL DEFAULT 0,

    error_message TEXT,

    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_import_jobs_type
        CHECK (import_type IN (
            'URL',
            'FILE',
            'PASTE_TEXT',
            'GITHUB',
            'NOTION'
        )),

    CONSTRAINT chk_import_jobs_status
        CHECK (status IN (
            'PROCESSING',
            'COMPLETED',
            'PARTIAL_SUCCESS',
            'FAILED'
        ))
);



CREATE TABLE knowledge_sources (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

	knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,

    import_job_id UUID REFERENCES import_jobs(id) ON DELETE SET NULL,

    -- 系统来源名称，更偏“文件/来源本身”
    -- UI 主标题优先显示 title，没有 title 时 fallback 到 source_name。
    source_name VARCHAR(255) NOT NULL,
	-- URL / PDF / DOCX / TXT / MD / PASTE_TEXT / GITHUB / NOTION
	source_type VARCHAR(30) NOT NULL,

	-- 文档自身标题，例如网页 title、PDF title，可为空
	title VARCHAR(255),
	-- URL / GitHub / Notion 来源地址
	original_url TEXT,

	-- FILE 用
	file_name VARCHAR(255),
	mime_type VARCHAR(100),
	file_size_bytes BIGINT,
	-- 文件 或者的原始存储位置
 	file_path TEXT,

    -- 内容去重 / 判断是否更新
    content_hash VARCHAR(128),

	-- UI 预览，只存前 300/500 字
	content_preview TEXT,

	-- PASTE_TEXT 可以存完整内容；URL 可选存清洗后文本
    raw_content TEXT,

	-- GitHub / Notion / 第三方集成用
 	external_id VARCHAR(255),
 	external_metadata JSONB NOT NULL DEFAULT '{}',

	-- PENDING / PROCESSING / COMPLETED / FAILED / DELETED
	status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
	error_message TEXT,

	chunk_count INTEGER NOT NULL DEFAULT 0,

	imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_knowledge_sources_type
        CHECK (source_type IN (
            'URL',
            'PDF',
            'DOCX',
            'TXT',
            'MD',
            'PASTE_TEXT',
            'GITHUB',
            'NOTION'
        )),

    CONSTRAINT chk_knowledge_sources_status
        CHECK (status IN (
            'PENDING',
            'PROCESSING',
            'COMPLETED',
            'FAILED',
            'DELETED'
        )),

    CONSTRAINT chk_knowledge_sources_chunk_count
        CHECK (chunk_count >= 0),

  	CONSTRAINT chk_knowledge_sources_file_size
        CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0)
);



CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    knowledge_base_id UUID NOT NULL
        REFERENCES knowledge_bases(id)
        ON DELETE CASCADE,

    source_id UUID NOT NULL
        REFERENCES knowledge_sources(id)
        ON DELETE CASCADE,

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    chunk_index INTEGER NOT NULL,

    content TEXT NOT NULL,

    token_count INTEGER,                   -- token 数量
    metadata JSONB NOT NULL DEFAULT '{}',  -- 页码、标题、URL、section 等

    qdrant_point_id VARCHAR(100),  				 -- 对应 Qdrant 里的 vector id

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_knowledge_chunks_chunk_index
        CHECK (chunk_index >= 0)
);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID,
    title VARCHAR(255),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    role VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_messages_session_id_created_at
ON chat_messages(session_id, created_at);




CREATE TABLE agent_tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    -- 关联触发这次工具调用的 assistant message，也可以为空
    message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,

    -- document_search / web_search / weather / calendar / email / tasks
    tool_name VARCHAR(100) NOT NULL,

    -- running / success / failed
    status VARCHAR(30) NOT NULL DEFAULT 'success',

    -- 工具入参
    input JSONB,

    -- 工具输出摘要，不建议存特别大的完整结果
    output JSONB,

    error_message TEXT,

    started_at TIMESTAMP NOT NULL DEFAULT now(),
    finished_at TIMESTAMP
);










