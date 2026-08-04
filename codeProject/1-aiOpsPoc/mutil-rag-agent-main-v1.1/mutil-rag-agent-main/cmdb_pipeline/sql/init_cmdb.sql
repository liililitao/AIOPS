-- ============================================================
-- CMDB 初始化 SQL — 容器启动时自动执行
-- ============================================================

-- 设备表: 核心表, 存放所有 IT 资产信息
CREATE TABLE IF NOT EXISTS cmdb_devices (
    id          SERIAL PRIMARY KEY,
    ip          VARCHAR(45)  NOT NULL UNIQUE,   -- 支持 IPv4/IPv6
    hostname    VARCHAR(255) NOT NULL,
    app_name    VARCHAR(255) NOT NULL,           -- 所属应用
    owner       VARCHAR(100) NOT NULL,           -- 负责人
    env         VARCHAR(20)  NOT NULL DEFAULT 'PROD',  -- PROD / UAT / TEST / DEV
    business_level VARCHAR(20) NOT NULL DEFAULT '一般', -- 核心 / 重要 / 一般
    room        VARCHAR(100),                    -- 机房位置
    os          VARCHAR(100),                    -- 操作系统
    description TEXT,                            -- 备注
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 变更日志表: 模拟 Flink CDC 要捕获的目标
-- 生产环境中 Flink CDC 读的是 PostgreSQL 的 WAL, 不需要这张表
-- 这里创建它是为了让你直观看到"变更有记录"
CREATE TABLE IF NOT EXISTS cmdb_change_log (
    id          SERIAL PRIMARY KEY,
    device_id   INT NOT NULL,
    operation   VARCHAR(10) NOT NULL,   -- INSERT / UPDATE / DELETE
    old_data    JSONB,                  -- 变更前数据
    new_data    JSONB,                  -- 变更后数据
    changed_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 触发器函数: 自动记录变更日志
-- ============================================================
CREATE OR REPLACE FUNCTION log_cmdb_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO cmdb_change_log (device_id, operation, new_data)
        VALUES (NEW.id, 'INSERT', row_to_json(NEW)::jsonb);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO cmdb_change_log (device_id, operation, old_data, new_data)
        VALUES (NEW.id, 'UPDATE', row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO cmdb_change_log (device_id, operation, old_data)
        VALUES (OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 触发器: 关联到 cmdb_devices 表
DROP TRIGGER IF EXISTS trg_cmdb_change ON cmdb_devices;
CREATE TRIGGER trg_cmdb_change
    AFTER INSERT OR UPDATE OR DELETE ON cmdb_devices
    FOR EACH ROW EXECUTE FUNCTION log_cmdb_change();

-- ============================================================
-- 初始种子数据 (与 alert_simulator.py 的 HOST_POOL 对齐)
-- ============================================================
INSERT INTO cmdb_devices (ip, hostname, app_name, owner, env, business_level, room, os) VALUES
    ('10.0.1.101',   'pay-gw-01',       '支付网关服务', '张三', 'PROD', '核心', 'A栋-3F-01', 'CentOS 7.9'),
    ('10.0.1.102',   'pay-gw-02',       '支付网关服务', '张三', 'PROD', '核心', 'A栋-3F-02', 'CentOS 7.9'),
    ('10.0.1.103',   'user-svc-01',     '用户中心',     '李四', 'PROD', '重要', 'A栋-3F-03', 'Ubuntu 22.04'),
    ('10.0.2.11',    'order-svc-01',    '订单服务',     '王五', 'PROD', '核心', 'B栋-2F-01', 'Ubuntu 22.04'),
    ('10.0.2.12',    'order-svc-02',    '订单服务',     '王五', 'PROD', '核心', 'B栋-2F-02', 'Ubuntu 22.04'),
    ('192.168.1.50', 'inventory-db',    '库存数据库',   '赵六', 'PROD', '重要', 'B栋-1F-01', 'CentOS 7.9'),
    ('192.168.1.51', 'cache-node-01',   '缓存集群',     '钱七', 'PROD', '一般', 'C栋-1F-01', 'CentOS 7.9'),
    ('172.16.0.10',  'kafka-broker-01', '消息队列',     '孙八', 'PROD', '重要', 'C栋-2F-01', 'Ubuntu 22.04'),
    ('172.16.0.11',  'es-node-01',      '搜索引擎',     '周九', 'PROD', '一般', 'C栋-2F-02', 'Ubuntu 22.04'),
    ('99.99.99.99',  'pay-gw-prod',     '支付网关服务', '张三', 'PROD', '核心', 'A栋-3F-04', 'CentOS 7.9')
ON CONFLICT (ip) DO NOTHING;

-- 通知: 初始化完成
DO $$
BEGIN
    RAISE NOTICE 'CMDB 初始化完成: % 条设备记录', (SELECT COUNT(*) FROM cmdb_devices);
END $$;
