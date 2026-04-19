import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { rpcCall } from "./lib/api";

type ChatLine = { role: "user" | "assistant"; content: string; id?: string };
type AgentOption = { id: string; name: string; desc: string };
type ToastType = "success" | "error" | "warning" | "info";

type ToastMessage = {
  id: string;
  type: ToastType;
  message: string;
};

type TaskLog = {
  id: string;
  timestamp: string;
  type: "info" | "success" | "error" | "warning" | "system";
  message: string;
  details?: string;
};

const Icons = {
  Folder: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>,
  File: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-9V8l-5-6z"/><polyline points="13 3 13 9 20 9"/></svg>,
  Clipboard: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>,
  Brain: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 4.5a2.5 2.5 0 0 0-4.96-.44 2.5 2.5 0 0 0-1.98 3 2.5 2.5 0 0 0-1.32 4.24 2.5 2.5 0 0 0 .73 3.45 2.5 2.5 0 0 0 2.53 3.75M12 4.5a2.5 2.5 0 0 1 4.96-.44 2.5 2.5 0 0 1 1.98 3 2.5 2.5 0 0 1 1.32 4.24 2.5 2.5 0 0 1-.73 3.45 2.5 2.5 0 0 1-2.53 3.75"/></svg>,
  Settings: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
  Refresh: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>,
  Sun: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  Moon: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>,
  Send: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>,
  Terminal: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>,
  Activity: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  User: () => <span style={{fontSize: 14}}>U</span>,
  Bot: () => <span style={{fontSize: 14, fontWeight: 600}}>E</span>,
  ChevronDown: () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>,
  MessageSquare: () => <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
};

function parentDirectory(path: string): string | null {
  const t = path.replace(/[/\\]+$/, "");
  const idx = Math.max(t.lastIndexOf("\\"), t.lastIndexOf("/"));
  if (idx <= 0) return null;
  return t.slice(0, idx);
}

export default function App() {
  const defaults: AgentOption[] = [
    { id: "default", name: "默认助手", desc: "通用任务处理" },
    { id: "code", name: "代码专家", desc: "代码审查与优化" },
    { id: "debug", name: "调试助手", desc: "问题定位与修复" },
    { id: "design", name: "设计助手", desc: "UI/UX 设计建议" }
  ];
  const modelMap: Record<string, string> = {
    "GLM-5": "glm-4",
    "Claude 4 Sonnet": "claude-sonnet-4-20250514",
    "Claude 4 Opus": "claude-opus-4-20250514",
    "GPT-4o": "gpt-4o",
    "GPT-4 Turbo": "gpt-4-turbo"
  };

  const PROVIDER_DEFAULT_ENDPOINTS: Record<string, string> = {
    openai: "https://api.openai.com/v1",
    anthropic: "https://api.anthropic.com",
    google: "https://generativelanguage.googleapis.com/v1beta",
    deepseek: "https://api.deepseek.com",
    zhipu: "https://open.bigmodel.cn/api/paas/v4"
  };

  const endpointForProvider = (provider: string, customEndpoint: string) => {
    if (provider === "custom") return customEndpoint.trim();
    return PROVIDER_DEFAULT_ENDPOINTS[provider] ?? "";
  };

  const [agentOptions, setAgentOptions] = useState<AgentOption[]>(defaults);
  const [selectedAgentId, setSelectedAgentId] = useState(defaults[0].id);
  const [token, setToken] = useState("evolver-secure-token-2026");
  const [sessionId, setSessionId] = useState("");
  const [message, setMessage] = useState("");
  const [chatLines, setChatLines] = useState<ChatLine[]>([]);
  const [serverStatus, setServerStatus] = useState("unknown");
  const [output, setOutput] = useState("");
  const [apiConfigSummary, setApiConfigSummary] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [leftTab, setLeftTab] = useState<"files" | "sessions" | "skills" | "memory">("skills");
  const [skillSubTab, setSkillSubTab] = useState<"agents" | "approvals" | "skills" | "mcp">("skills");
  const [rightTab, setRightTab] = useState<"terminal" | "files" | "status">("status");
  const [modelOpen, setModelOpen] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState("GLM-5");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [language, setLanguage] = useState("zh-CN");
  const [kpiMode, setKpiMode] = useState(false);
  const [showTokenStats, setShowTokenStats] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [taskLogs, setTaskLogs] = useState<TaskLog[]>([]);
  const [selfEvolutionGoal, setSelfEvolutionGoal] = useState("优化技能、记忆和 MCP 集成");
  const [selfEvolutionHistory, setSelfEvolutionHistory] = useState<Array<{goal: string; recommendations: Array<{area: string; action: string; priority: number; reason: string}>; timestamp: number}>>([]);
  const [workItems, setWorkItems] = useState<Array<{id: string; title: string; area: string; action: string; priority: number; reason: string; status: string; created_at: number; source_goal: string}>>([]);
  const [recentFailures, setRecentFailures] = useState<Array<{session_id: string; agent_id: string; model?: string; message: string; reason: string; timestamp: number}>>([]);
  const [localApiKeys, setLocalApiKeys] = useState<Record<string, string>>({});
  const [apiConfig, setApiConfig] = useState<{
    openaiApiKey: string;
    anthropicApiKey: string;
    googleApiKey: string;
    deepseekApiKey: string;
    customEndpoint: string;
    customApiKey: string;
    modelName: string;
  }>({
    openaiApiKey: "",
    anthropicApiKey: "",
    googleApiKey: "",
    deepseekApiKey: "",
    customEndpoint: "",
    customApiKey: "",
    modelName: ""
  });
  const [customModels, setCustomModels] = useState<string[]>([]);
  const [activeProvider, setActiveProvider] = useState<string>("openai");
  const [apiConfigModalOpen, setApiConfigModalOpen] = useState<boolean>(false);
  const [skills, setSkills] = useState<Array<{id: string; name: string; description: string; scope?: string}>>([]);
  const [pendingApprovals, setPendingApprovals] = useState<Array<{skill_id: string; skill_name: string; confidence: number; details?: Record<string, unknown>}>>([]);
  const [mcpServers, setMcpServers] = useState<Array<{server_id: string; type: string; command: string; tools_count: number; connected: boolean}>>([]);
  const [mcpTools, setMcpTools] = useState<Array<{name: string; description: string; source?: string; server_id?: string}>>([]);
  const [mcpCallResult, setMcpCallResult] = useState<string>("");
  const [mcpCallHistory, setMcpCallHistory] = useState<Array<{id: string; serverId: string; toolName: string; result: string; timestamp: number}>>([]);
  const [mcpLastRefreshedAt, setMcpLastRefreshedAt] = useState<number>(0);
  const [mcpAutoRefreshEnabled, setMcpAutoRefreshEnabled] = useState<boolean>(true);
  const [mcpConnectForm, setMcpConnectForm] = useState<{server_id: string; command: string; args: string}>({server_id: "", command: "", args: ""});
  const [mcpCallForm, setMcpCallForm] = useState<{server_id: string; tool_name: string; arguments_json: string}>({server_id: "", tool_name: "", arguments_json: "{}"});
  const [modelConfig, setModelConfig] = useState<{
    provider: string;
    apiKey: string;
    modelName: string;
    customEndpoint: string;
  }>({
    provider: "openai",
    apiKey: "",
    modelName: "",
    customEndpoint: ""
  });
  const [projects, setProjects] = useState<Array<{project_id: string; name: string; description: string}>>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("default");
  const [projectModalOpen, setProjectModalOpen] = useState<boolean>(false);
  const [newProjectName, setNewProjectName] = useState<string>("");
  const [newProjectDescription, setNewProjectDescription] = useState<string>("");
  const [memorySearchQuery, setMemorySearchQuery] = useState<string>("");
  const [memoryResults, setMemoryResults] = useState<Array<{content: string; type: string; timestamp: number}>>([]);
  const [memorySaveContent, setMemorySaveContent] = useState<string>("");
  const [localFiles, setLocalFiles] = useState<Array<{name: string; path: string; isDirectory: boolean}>>([]);
  const [currentDirectory, setCurrentDirectory] = useState<string>("");
  const [previewFilePath, setPreviewFilePath] = useState<string>("");
  const [previewFileContent, setPreviewFileContent] = useState<string>("");
  const [shellCmd, setShellCmd] = useState<string>("");
  const authToken = useMemo(() => token.trim(), [token]);
  const selectedAgent = agentOptions.find((a) => a.id === selectedAgentId) ?? agentOptions[0];

  const barRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatLines]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const loadProjects = useCallback(async () => {
    try {
      const result = await rpcCall<Array<{project_id: string; name: string; description: string}>>(
        { method: "list_projects", params: {} }, authToken
      );
      if (Array.isArray(result)) setProjects(result);
    } catch (e) {
      addTaskLog("warning", "无法加载项目列表", `错误: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [authToken]);

  const loadInitialData = useCallback(async () => {
    try {
      const agents = await rpcCall<Array<{ id: string; name: string; description?: string }>>(
        { method: "get_agents" },
        authToken
      );
      if (Array.isArray(agents) && agents.length > 0) {
        const normalized = agents.map((item) => ({
          id: item.id,
          name: item.name,
          desc: item.description ?? ""
        }));
        setAgentOptions(normalized);
        setSelectedAgentId(normalized[0].id);
      }
    } catch (e) {
      addTaskLog("warning", "无法连接后端服务器", `http://127.0.0.1:16888/rpc - ${e instanceof Error ? e.message : String(e)}`);
    }
    await loadProjects();
  }, [authToken, loadProjects]);

  /** 将当前模型设置页的供应商配置推到后端，避免只改了 UI 未点「保存」就发 chat */
  const pushActiveApiConfigToBackend = useCallback(async () => {
    const key = modelConfig.apiKey.trim();
    const modelName = modelConfig.modelName.trim();
    if (!key || !modelName) return;
    const ep = endpointForProvider(modelConfig.provider, modelConfig.customEndpoint);
    try {
      await rpcCall<{ success: boolean }>(
        {
          method: "update_api_config",
          params: {
            config: {
              [modelConfig.provider]: {
                api_key: key,
                model_name: modelName,
                ...(ep ? { endpoint: ep } : {})
              }
            }
          }
        },
        authToken
      );
    } catch {
      /* 已保存或仅用环境变量时可忽略 */
    }
  }, [modelConfig.apiKey, modelConfig.modelName, modelConfig.provider, modelConfig.customEndpoint, authToken]);

  // 从localStorage加载API配置
  useEffect(() => {
    const savedConfig = localStorage.getItem('evolver-api-config');
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig);
        setApiConfig(config);
        setModelConfig({
          provider: config.provider || 'openai',
          apiKey: config.apiKey || '',
          modelName: config.modelName || '',
          customEndpoint: config.customEndpoint || ''
        });
      } catch (e) {
        console.error('Failed to load saved config:', e);
      }
    }
  }, []);

  // 保存API配置到localStorage
  const saveApiConfigToLocalStorage = (config: any) => {
    try {
      localStorage.setItem('evolver-api-config', JSON.stringify(config));
    } catch (e) {
      console.error('Failed to save config:', e);
    }
  };

  // 加载历史会话列表
  const loadSessions = async () => {
    try {
      const sessions = await rpcCall<Array<{id: string; model: string; created_at: number; updated_at: number}>>(
        { method: "list_sessions", params: {} }, authToken
      );
      if (Array.isArray(sessions) && sessions.length > 0) {
        // 选择最新的会话
        const latestSession = sessions.sort((a, b) => b.updated_at - a.updated_at)[0];
        setSessionId(latestSession.id);
        // 加载会话历史
        await loadSessionHistory(latestSession.id);
      }
    } catch (e) {
      addTaskLog("warning", "无法加载会话列表", `错误: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  // 加载会话历史
  const loadSessionHistory = async (sessionId: string) => {
    try {
      const history = await rpcCall<{ session_id: string; messages: Array<{ role: string; content: string }> }>(
        { method: "get_session_history", params: { session_id: sessionId } }, authToken
      );
      if (history && history.messages) {
        // 转换消息格式以匹配前端的ChatLine类型
        const formattedMessages = history.messages.map((msg, index) => ({
          role: msg.role as "user" | "assistant",
          content: msg.content,
          id: `history-${index}`
        }));
        setChatLines(formattedMessages);
        addTaskLog("success", `加载会话历史成功: ${formattedMessages.length} 条消息`);
      }
    } catch (e) {
      addTaskLog("warning", "无法加载会话历史", `错误: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (!cancelled) {
        for (let attempt = 0; attempt < 12 && !cancelled; attempt++) {
          try {
            await rpcCall({ method: "get_agents" }, authToken);
            await loadInitialData();
            await loadSessions();
            break;
          } catch {
            await new Promise((r) => setTimeout(r, 450));
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadInitialData, authToken]);

  const showToast = (type: ToastType, message: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 3000);
  };

  const createProject = async () => {
    if (!newProjectName.trim()) {
      showToast("error", "项目名称不能为空");
      return;
    }
    try {
      const result = await rpcCall<{success: boolean; project_id: string}>(
        { method: "create_project", params: { name: newProjectName.trim(), description: newProjectDescription } }, authToken
      );
      if (result?.success) {
        showToast("success", `项目 ${newProjectName} 创建成功`);
        setProjectModalOpen(false);
        setNewProjectName("");
        setNewProjectDescription("");
        await loadProjects();
      }
    } catch (e) {
      showToast("error", `创建项目失败: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const setActiveProject = async (projectId: string) => {
    try {
      const result = await rpcCall<{success: boolean; active_project_id: string}>(
        { method: "set_active_project", params: { project_id: projectId } }, authToken
      );
      if (result?.success) {
        setSelectedProjectId(projectId);
        showToast("success", `已切换到项目 ${projectId}`);
      }
    } catch (e) {
      showToast("error", `切换项目失败: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const searchMemory = async () => {
    if (!memorySearchQuery.trim()) {
      showToast("warning", "请输入搜索关键词");
      return;
    }
    try {
      const result = await rpcCall<Array<{content: string; type: string; timestamp: number}>>(
        { method: "search_memory", params: { query: memorySearchQuery, scope_id: selectedProjectId } }, authToken
      );
      if (Array.isArray(result)) {
        setMemoryResults(result);
        showToast("success", `找到 ${result.length} 条记忆`);
      }
    } catch (e) {
      showToast("error", `搜索记忆失败: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const saveMemory = async () => {
    if (!memorySaveContent.trim()) {
      showToast("warning", "请输入记忆内容");
      return;
    }
    try {
      const result = await rpcCall<{success: boolean}>(
        { method: "save_memory", params: { content: memorySaveContent, project_id: selectedProjectId } }, authToken
      );
      if (result?.success) {
        setMemorySaveContent("");
        showToast("success", "记忆保存成功");
        // 重新搜索以更新结果
        if (memorySearchQuery.trim()) {
          await searchMemory();
        }
      }
    } catch (e) {
      showToast("error", `保存记忆失败: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const loadSkills = async () => {
    try {
      const result = await rpcCall<Array<{id: string; name: string; description: string; scope?: string}>>(
        { method: "get_skills", params: {} }, authToken
      );
      if (Array.isArray(result)) setSkills(result);
    } catch { setSkills([]); }
  };

  const loadPendingApprovals = async () => {
    try {
      const result = await rpcCall<Array<{skill_id: string; skill_name: string; confidence: number; details?: Record<string, unknown>}>>(
        { method: "get_pending_approvals", params: {} }, authToken
      );
      if (Array.isArray(result)) setPendingApprovals(result);
    } catch { setPendingApprovals([]); }
  };

  const handleApproveSkill = async (skillId: string) => {
    try {
      await rpcCall({ method: "approve_skill", params: { skill_id: skillId } }, authToken);
      showToast("success", "技能已批准");
      addTaskLog("success", `技能 ${skillId} 已批准`);
      loadPendingApprovals();
    } catch (e) { showToast("error", "审批失败"); }
  };

  const handleRejectSkill = async (skillId: string) => {
    try {
      await rpcCall({ method: "reject_skill", params: { skill_id: skillId, reason: "用户拒绝" } }, authToken);
      showToast("warning", "技能已拒绝");
      addTaskLog("warning", `技能 ${skillId} 已拒绝`);
      loadPendingApprovals();
    } catch (e) { showToast("error", "拒绝失败"); }
  };

  const refreshMcpState = async () => {
    await Promise.all([loadMcpServers(), loadMcpTools()]);
    setMcpLastRefreshedAt(Date.now());
  };

  const loadMcpServers = async () => {
    try {
      const result = await rpcCall<Array<{server_id: string; type: string; command: string; tools_count: number; connected: boolean}>>(
        { method: "list_mcp_servers", params: {} }, authToken
      );
      if (Array.isArray(result)) setMcpServers(result);
    } catch { setMcpServers([]); }
  };

  const loadMcpTools = async (serverId?: string) => {
    try {
      const result = await rpcCall<Array<{name: string; description: string; source?: string; server_id?: string}>>(
        { method: "list_mcp_tools", params: serverId ? { server_id: serverId } : {} }, authToken
      );
      if (Array.isArray(result)) setMcpTools(result);
    } catch { setMcpTools([]); }
  };

  const loadSelfEvolutionHistory = async () => {
    try {
      const result = await rpcCall<Array<{goal: string; recommendations: Array<{area: string; action: string; priority: number; reason: string}>; timestamp: number}>>(
        { method: "get_self_evolution_history", params: {} },
        authToken
      );
      if (Array.isArray(result)) setSelfEvolutionHistory(result);
    } catch {
      setSelfEvolutionHistory([]);
    }
  };

  const loadWorkItems = async () => {
    try {
      const result = await rpcCall<Array<{id: string; title: string; area: string; action: string; priority: number; reason: string; status: string; created_at: number; source_goal: string}>>(
        { method: "list_work_items", params: {} },
        authToken
      );
      if (Array.isArray(result)) setWorkItems(result);
    } catch {
      setWorkItems([]);
    }
  };

  const loadRecentFailures = async () => {
    try {
      const result = await rpcCall<Array<{session_id: string; agent_id: string; model?: string; message: string; reason: string; timestamp: number}>>(
        { method: "get_recent_failures", params: { limit: 10 } },
        authToken
      );
      if (Array.isArray(result)) setRecentFailures(result);
    } catch {
      setRecentFailures([]);
    }
  };

  const handleSelfEvolve = async () => {
    if (!selfEvolutionGoal.trim()) {
      showToast("warning", "请输入进化目标");
      return;
    }
    try {
      setIsLoading(true);
      const result = await rpcCall<{ success: boolean; recommendations?: Array<{area: string; action: string; priority: number; reason: string}>; history_size?: number }>(
        { method: "self_evolve", params: { goal: selfEvolutionGoal, signals: { agent_id: selectedAgentId, model: selectedModel }, scope_id: selectedProjectId } },
        authToken
      );
      showToast("success", `自我进化建议已生成 (${result.history_size ?? 0})`);
      await loadSelfEvolutionHistory();
      await loadWorkItems();
      await loadRecentFailures();
      addTaskLog("success", "完成一次自我进化分析", `建议 ${result.recommendations?.length ?? 0} 条`);
    } catch (e) {
      showToast("error", `自我进化失败: ${String(e)}`);
      addTaskLog("error", `自我进化失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const validateApiConfig = async () => {
    try {
      setIsLoading(true);
      const ep = endpointForProvider(modelConfig.provider, modelConfig.customEndpoint);
      const cfg: Record<string, { api_key: string; model_name: string; endpoint?: string }> = {
        [modelConfig.provider]: {
          api_key: modelConfig.apiKey.trim(),
          model_name: modelConfig.modelName.trim(),
          ...(ep ? { endpoint: ep } : {})
        }
      };
      const result = await rpcCall<{ valid: boolean; errors: string[]; warnings: string[] }>(
        { method: "validate_api_config", params: { config: cfg } },
        authToken
      );

      if (result.valid) {
        showToast("success", "API配置验证通过");
        if (result.warnings.length > 0) {
          result.warnings.forEach((warning) => {
            showToast("warning", warning);
          });
        }
        // 保存配置到localStorage
        saveApiConfigToLocalStorage(modelConfig);
      } else {
        result.errors.forEach((error) => {
          showToast("error", error);
        });
      }
    } catch (e) {
      showToast("error", `验证失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const listDirectory = async (dirPath: string) => {
    const filesResult = await rpcCall<Array<{ name: string; path: string; isDirectory: boolean }>>(
      { method: "list_local_files", params: { path: dirPath } },
      authToken
    );
    setLocalFiles(filesResult);
    setCurrentDirectory(dirPath);
  };

  const browseLocalFiles = async () => {
    try {
      setIsLoading(true);
      const result = await rpcCall<{ path: string | null; cancelled: boolean }>(
        { method: "select_directory", params: {} },
        authToken
      );

      if (!result.cancelled && result.path) {
        showToast("success", `已选择目录: ${result.path}`);
        await listDirectory(result.path);
      } else {
        showToast("info", "已取消选择");
      }
    } catch (e) {
      showToast("error", `浏览文件失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const enterLocalDirectory = async (dirPath: string) => {
    try {
      setIsLoading(true);
      await listDirectory(dirPath);
    } catch (e) {
      showToast("error", `进入目录失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const goUpLocalDirectory = async () => {
    if (!currentDirectory) return;
    const parent = parentDirectory(currentDirectory);
    if (!parent) {
      showToast("info", "已在顶层");
      return;
    }
    await enterLocalDirectory(parent);
  };

  const openLocalFile = async (path: string) => {
    try {
      setIsLoading(true);
      const result = await rpcCall<{ content: string }>({ method: "read_local_file", params: { path } }, authToken);
      setPreviewFilePath(path);
      setPreviewFileContent(result.content ?? "");
      setRightTab("files");
      showToast("success", `已读取: ${path}`);
    } catch (e) {
      showToast("error", `打开文件失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const runShellCommand = async () => {
    const cmd = shellCmd.trim();
    if (!cmd) {
      showToast("warning", "请输入命令");
      return;
    }
    try {
      setIsLoading(true);
      addTaskLog("info", `执行: ${cmd}`);
      const r = await rpcCall<{
        ok: boolean;
        stdout?: string;
        stderr?: string;
        error?: string;
        returncode?: number;
        diagnostic?: { effective_listen_host?: string; raw_http_host?: string };
      }>({ method: "exec_shell", params: { command: cmd } }, authToken);
      const text = r.ok
        ? `exit ${r.returncode ?? -1}\n${r.stdout ?? ""}${r.stderr ? `\n${r.stderr}` : ""}`
        : `${r.error ?? "执行失败"}${r.diagnostic ? `\n诊断: ${JSON.stringify(r.diagnostic)}` : ""}`;
      setOutput(text);
      addTaskLog(r.ok ? "success" : "error", `shell 完成`, text.slice(0, 600));
      setRightTab("terminal");
    } catch (e) {
      showToast("error", `执行失败: ${String(e)}`);
      addTaskLog("error", "shell 失败", String(e));
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnectMcp = async () => {
    if (!mcpConnectForm.server_id || !mcpConnectForm.command) {
      showToast("warning", "请填写服务器ID和命令");
      return;
    }
    try {
      const args = mcpConnectForm.args ? mcpConnectForm.args.split(" ").filter(Boolean) : [];
      await rpcCall({ method: "connect_mcp_server", params: { server_id: mcpConnectForm.server_id, command: mcpConnectForm.command, args } }, authToken);
      showToast("success", `MCP服务器 ${mcpConnectForm.server_id} 已连接`);
      addTaskLog("success", `MCP服务器 ${mcpConnectForm.server_id} 已连接`);
      setMcpConnectForm({server_id: "", command: "", args: ""});
      loadMcpServers();
    } catch (e) { showToast("error", "连接失败"); }
  };

  const handleDisconnectMcp = async (serverId: string) => {
    try {
      await rpcCall({ method: "disconnect_mcp_server", params: { server_id: serverId } }, authToken);
      showToast("info", `MCP服务器 ${serverId} 已断开`);
      addTaskLog("info", `MCP服务器 ${serverId} 已断开`);
      loadMcpServers();
      loadMcpTools();
    } catch (e) { showToast("error", "断开失败"); }
  };

  const loadMcpToolsForServer = async (serverId: string) => {
    setMcpCallForm((prev) => ({ ...prev, server_id: serverId }));
    await loadMcpTools(serverId);
  };

  const handleCallMcpTool = async () => {
    if (!mcpCallForm.server_id || !mcpCallForm.tool_name) {
      showToast("warning", "请填写服务器ID和工具名");
      return;
    }
    try {
      const argumentsObj = mcpCallForm.arguments_json.trim() ? JSON.parse(mcpCallForm.arguments_json) : {};
      const result = await rpcCall(
        { method: "call_mcp_tool", params: { tool_name: mcpCallForm.tool_name, parameters: argumentsObj, server_id: mcpCallForm.server_id } },
        authToken
      );
      const rendered = JSON.stringify(result, null, 2);
      setOutput(rendered);
      setMcpCallResult(rendered);
      setMcpCallHistory((prev) => [
        ...prev.slice(-19),
        {
          id: Math.random().toString(36).substr(2, 9),
          serverId: mcpCallForm.server_id,
          toolName: mcpCallForm.tool_name,
          result: rendered,
          timestamp: Date.now(),
        }
      ]);
      showToast("success", `MCP工具 ${mcpCallForm.tool_name} 调用成功`);
      addTaskLog("success", `MCP工具 ${mcpCallForm.tool_name} 调用成功`);
    } catch (e) {
      showToast("error", `MCP工具调用失败: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const addTaskLog = (type: TaskLog["type"], message: string, details?: string) => {
    const now = new Date();
    const timestamp = now.toLocaleTimeString("zh-CN", { hour12: false });
    const log: TaskLog = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp,
      type,
      message,
      details
    };
    setTaskLogs((prev) => [...prev.slice(-99), log]);
  };

  async function refreshServerStatus() {
    try {
      await rpcCall({ method: "health" }, authToken);
      setServerStatus("已连接");
      showToast("success", "后端可用");
    } catch (e) {
      setServerStatus("未连接");
      showToast("error", `后端不可用: ${String(e)}`);
    }
  }

  async function startServer() {
    setOutput("请在仓库根执行：python start.py（会启动后端与 Vite），或另开终端运行 .venv\\Scripts\\python.exe -m evolver.server 与 npm run dev");
    showToast("info", "后端由本机 Python 进程提供，请用 python start.py 启动");
    addTaskLog("warning", "浏览器内无法代你启动系统进程，请用 start.py 或手动启动后端");
  }

  async function stopServer() {
    setOutput("停止后端：请在运行 evolver.server 的终端按 Ctrl+C，或关闭对应窗口。");
    showToast("info", "浏览器内无法结束本机 Python 进程");
    addTaskLog("warning", "请在终端手动停止后端");
  }

  async function createSession() {
    try {
      setIsLoading(true);
      addTaskLog("info", "正在创建新会话...");
      const id = await rpcCall<string>({ method: "create_session" }, authToken);
      // 确保id是一个字符串，不是一个对象
      if (typeof id === 'string') {
        setSessionId(id);
        setOutput(`session created: ${id}`);
        addTaskLog("success", `会话创建成功: ${id}`);
        showToast("success", `会话创建成功: ${id}`);
      } else {
        throw new Error(`无效的会话ID: ${typeof id}`);
      }
    } catch (e) {
      setOutput(String(e));
      addTaskLog("error", `创建会话失败: ${String(e)}`);
      showToast("error", `创建会话失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  }

  async function sendChat() {
    if (!sessionId || !message.trim()) {
      if (!sessionId) {
        showToast("warning", "请先创建会话");
        addTaskLog("warning", "发送失败：未创建会话");
      } else if (!message.trim()) {
        showToast("warning", "请输入消息内容");
        addTaskLog("warning", "发送失败：消息为空");
      }
      return;
    }
    const userLine: ChatLine = { 
      role: "user", 
      content: message,
      id: Math.random().toString(36).substr(2, 9)
    };
    setChatLines((prev) => [...prev, userLine]);
    setMessage("");
    try {
      setIsLoading(true);
      addTaskLog("info", `正在发送消息到 ${selectedAgent.name}...`, `模型: ${selectedModel}`);
      await pushActiveApiConfigToBackend();
      const result = await rpcCall<{ final_response?: string }>(
        {
          method: "chat",
          params: {
            session_id: sessionId,
            message,
            agent_id: selectedAgentId,
            model: modelMap[selectedModel] ?? selectedModel,
            project_id: selectedProjectId,
            auth_token: authToken || undefined
          }
        },
        authToken
      );
      const reply = result.final_response ?? "";
      setChatLines((prev) => [...prev, { 
        role: "assistant", 
        content: reply,
        id: Math.random().toString(36).substr(2, 9)
      }]);
      setOutput(reply);
      addTaskLog("success", "消息处理完成", `${reply.length} 字符`);
      showToast("success", "消息发送成功");
    } catch (e) {
      setOutput(String(e));
      addTaskLog("error", `消息发送失败: ${String(e)}`);
      showToast("error", `发送消息失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">E</div>
            <span className="logo-text">Evolver</span>
          </div>
        </div>
        <div className="sidebar-tabs">
          <button className={`sidebar-tab ${leftTab === "files" ? "active" : ""}`} onClick={() => setLeftTab("files")}>
            <Icons.Folder /> 文件
          </button>
          <button className={`sidebar-tab ${leftTab === "sessions" ? "active" : ""}`} onClick={() => setLeftTab("sessions")}>
            <Icons.Clipboard /> 会话
          </button>
          <button className={`sidebar-tab ${leftTab === "skills" ? "active" : ""}`} onClick={() => setLeftTab("skills")}>
            <Icons.Brain /> 技能
          </button>
          <button className={`sidebar-tab ${leftTab === "memory" ? "active" : ""}`} onClick={() => setLeftTab("memory")}>
            <Icons.Clipboard /> 记忆
          </button>
        </div>
        <div className="sidebar-content">
          {leftTab === "files" && (
            <div className="file-tree">
              <div className="file-item active" onClick={() => browseLocalFiles()}>
                <span className="file-icon folder"><Icons.Folder /></span>
                <span className="file-name">选择本地目录…</span>
              </div>
              {currentDirectory ? (
                <>
                  <div className="file-item" style={{ fontSize: 11, opacity: 0.75, cursor: "default" }} title={currentDirectory}>
                    {currentDirectory.length > 36 ? `…${currentDirectory.slice(-34)}` : currentDirectory}
                  </div>
                  <div className="file-item" onClick={(e) => { e.stopPropagation(); goUpLocalDirectory(); }} style={{ fontSize: 12 }}>
                    <span className="file-icon folder"><Icons.Folder /></span>
                    <span className="file-name">↑ 上级目录</span>
                  </div>
                  {localFiles.map((f) => (
                    <div
                      key={f.path}
                      className={`file-item ${f.isDirectory ? "" : "child"}`}
                      onClick={() => (f.isDirectory ? enterLocalDirectory(f.path) : openLocalFile(f.path))}
                    >
                      <span className={`file-icon ${f.isDirectory ? "folder" : "ts"}`}>
                        {f.isDirectory ? <Icons.Folder /> : <Icons.File />}
                      </span>
                      <span className="file-name">{f.name}</span>
                    </div>
                  ))}
                </>
              ) : (
                <div className="empty-state" style={{ padding: "12px 8px" }}>
                  <span className="empty-sub">点击上方选择目录后可浏览与打开文件</span>
                </div>
              )}
            </div>
          )}
          {leftTab === "sessions" && (
            <div className="session-list">
              <button className="session-item active">
                <span className="session-icon"><Icons.Clipboard /></span>
                <div className="session-info">
                  <div className="session-title">当前会话</div>
                  <div className="session-time">{sessionId || "未创建"}</div>
                </div>
              </button>
            </div>
          )}
          {leftTab === "skills" && (
            <>
              <div className="skill-sub-tabs">
                <button className={`skill-sub-tab ${skillSubTab === "skills" ? "active" : ""}`} onClick={() => { setSkillSubTab("skills"); loadSkills(); }}>技能</button>
                <button className={`skill-sub-tab ${skillSubTab === "agents" ? "active" : ""}`} onClick={() => setSkillSubTab("agents")}>智能体</button>
                <button className={`skill-sub-tab ${skillSubTab === "approvals" ? "active" : ""}`} onClick={() => { setSkillSubTab("approvals"); loadPendingApprovals(); }}>审批</button>
                <button className={`skill-sub-tab ${skillSubTab === "mcp" ? "active" : ""}`} onClick={() => { setSkillSubTab("mcp"); refreshMcpState(); }}>MCP</button>
              </div>
              {skillSubTab === "skills" && (
                <div className="skill-list">
                  {skills.length === 0 ? (
                    <div className="empty-state">
                      <span className="empty-icon">✨</span>
                      <span>暂无技能</span>
                      <span className="empty-sub">点击下方按钮加载或创建技能</span>
                    </div>
                  ) : (
                    skills.map((skill) => (
                      <div key={skill.id} className="skill-item">
                        <div className="skill-info">
                          <div className="skill-name">{skill.name}</div>
                          <div className="skill-desc">{skill.description}</div>
                          {skill.scope ? <div className="skill-meta">scope: {skill.scope}</div> : null}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
              {skillSubTab === "agents" && (
                <div className="skill-list">
                  {agentOptions.map((agent) => (
                    <button
                      key={agent.id}
                      className={`skill-item ${selectedAgentId === agent.id ? "active" : ""}`}
                      onClick={() => {
                        setSelectedAgentId(agent.id);
                      }}
                    >
                      <div className={`skill-icon ${agent.id}`}>{agent.id === "code" ? "C" : agent.id === "debug" ? "D" : agent.id === "design" ? "U" : "AI"}</div>
                      <div className="skill-info">
                        <div className="skill-name">{agent.name}</div>
                        <div className="skill-desc">{agent.desc}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {skillSubTab === "approvals" && (
                <div className="approval-list">
                  {pendingApprovals.length === 0 ? (
                    <div className="empty-state">
                      <span className="empty-icon">✓</span>
                      <span>暂无待审批技能</span>
                      <span className="empty-sub">所有技能均已审批</span>
                    </div>
                  ) : (
                    pendingApprovals.map((approval) => (
                      <div key={approval.skill_id} className="approval-item">
                        <div className="approval-header">
                          <div className="approval-name">{approval.skill_name}</div>
                          <div className="approval-confidence">置信度: {(approval.confidence * 100).toFixed(0)}%</div>
                        </div>
                        <div className="approval-details">
                          {approval.details?.steps_count ? <span>步骤: {Number(approval.details.steps_count)}</span> : null}
                          {approval.details?.tools_used ? <span>工具: {String((approval.details.tools_used as string[]).join(", "))}</span> : null}
                        </div>
                        <div className="approval-actions">
                          <button className="approval-btn approve" onClick={() => handleApproveSkill(approval.skill_id)}>批准</button>
                          <button className="approval-btn reject" onClick={() => handleRejectSkill(approval.skill_id)}>拒绝</button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
              {skillSubTab === "mcp" && (
                <div className="mcp-panel">
                  <div className="mcp-panel-header">
                    <div className="mcp-section-title">MCP 服务器</div>
                    <div className="mcp-header-actions">
                      <span className="mcp-last-refresh">
                        {mcpLastRefreshedAt ? `更新: ${new Date(mcpLastRefreshedAt).toLocaleTimeString("zh-CN", {hour12: false})}` : "未更新"}
                      </span>
                      <label className="mcp-auto-refresh-toggle">
                        <input 
                          type="checkbox" 
                          checked={mcpAutoRefreshEnabled} 
                          onChange={(e) => setMcpAutoRefreshEnabled(e.target.checked)} 
                        />
                        自动刷新
                      </label>
                      <button className="mcp-refresh-btn" onClick={refreshMcpState}>🔄 刷新</button>
                    </div>
                  </div>
                  <div className="mcp-server-list">
                    {mcpServers.length === 0 ? (
                      <div className="empty-state">
                        <span className="empty-icon">🔌</span>
                        <span>暂无MCP服务器</span>
                        <span className="empty-sub">添加服务器以扩展工具能力</span>
                      </div>
                    ) : (
                      mcpServers.map((server) => (
                        <div key={server.server_id} className={`mcp-server-item ${server.connected ? "connected" : ""}`}>
                          <div className="mcp-server-info">
                            <div className="mcp-server-name">{server.server_id}</div>
                            <div className="mcp-server-meta">{server.command} · {server.tools_count} 工具</div>
                          </div>
                          <div className={`mcp-status-dot ${server.connected ? "on" : "off"}`} />
                          <button className="mcp-disconnect-btn" onClick={() => handleDisconnectMcp(server.server_id)}>断开</button>
                          <button className="mcp-connect-btn" onClick={() => loadMcpToolsForServer(server.server_id)}>查看工具</button>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="mcp-connect-form">
                    <input className="mcp-input" placeholder="服务器 ID" value={mcpConnectForm.server_id} onChange={(e) => setMcpConnectForm({...mcpConnectForm, server_id: e.target.value})} />
                    <input className="mcp-input" placeholder="命令 (如 npx @modelcontextprotocol/server-filesystem)" value={mcpConnectForm.command} onChange={(e) => setMcpConnectForm({...mcpConnectForm, command: e.target.value})} />
                    <input className="mcp-input" placeholder="参数 (空格分隔)" value={mcpConnectForm.args} onChange={(e) => setMcpConnectForm({...mcpConnectForm, args: e.target.value})} />
                    <button className="mcp-connect-btn" onClick={handleConnectMcp}>连接</button>
                  </div>

                  <div className="mcp-section-title" style={{marginTop: 16}}>MCP 工具</div>
                  <div className="mcp-server-list">
                    {mcpTools.length === 0 ? (
                      <div className="empty-state">
                        <span className="empty-icon">🛠️</span>
                        <span>暂无MCP工具</span>
                        <span className="empty-sub">先连接一个服务器以发现工具</span>
                      </div>
                    ) : (
                      mcpTools.map((tool) => (
                        <div key={`${tool.server_id || ""}:${tool.name}`} className="mcp-server-item">
                          <div className="mcp-server-info">
                            <div className="mcp-server-name">{tool.name}</div>
                            <div className="mcp-server-meta">{tool.server_id || "unknown"} · {tool.description || "无描述"}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="mcp-section-title" style={{marginTop: 16}}>调用工具</div>
                  <div className="mcp-connect-form">
                    <input className="mcp-input" placeholder="服务器 ID" value={mcpCallForm.server_id} onChange={(e) => setMcpCallForm({...mcpCallForm, server_id: e.target.value})} />
                    <input className="mcp-input" placeholder="工具名" value={mcpCallForm.tool_name} onChange={(e) => setMcpCallForm({...mcpCallForm, tool_name: e.target.value})} />
                    <textarea className="mcp-input" placeholder='参数 JSON，例如 {"path":"/tmp"}' value={mcpCallForm.arguments_json} onChange={(e) => setMcpCallForm({...mcpCallForm, arguments_json: e.target.value})} rows={4} />
                    <button className="mcp-connect-btn" onClick={handleCallMcpTool}>调用</button>
                  </div>
                  <div className="mcp-section-title" style={{marginTop: 16}}>调用结果</div>
                  <div className="mcp-result-box">
                    {mcpCallResult ? <pre>{mcpCallResult}</pre> : <div className="empty-state"><span className="empty-icon">📨</span><span>暂无调用结果</span></div>}
                  </div>
                  <div className="mcp-section-title" style={{marginTop: 16}}>调用历史</div>
                  <div className="mcp-server-list">
                    {mcpCallHistory.length === 0 ? (
                      <div className="empty-state">
                        <span className="empty-icon">🕒</span>
                        <span>暂无调用历史</span>
                        <span className="empty-sub">最近的工具调用会显示在这里</span>
                      </div>
                    ) : (
                      mcpCallHistory.map((item) => (
                        <div key={item.id} className="mcp-server-item">
                          <div className="mcp-server-info">
                            <div className="mcp-server-name">{item.toolName}</div>
                            <div className="mcp-server-meta">{item.serverId} · {new Date(item.timestamp).toLocaleTimeString("zh-CN", { hour12: false })}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </>
          )}
          {leftTab === "memory" && (
            <div className="memory-panel">
              <div className="memory-section-title">记忆管理</div>
              <div className="memory-search-form">
                <input 
                  className="mcp-input" 
                  placeholder="搜索记忆..." 
                  value={memorySearchQuery} 
                  onChange={(e) => setMemorySearchQuery(e.target.value)} 
                />
                <button className="mcp-connect-btn" onClick={searchMemory}>搜索</button>
              </div>
              <div className="memory-results">
                {memoryResults.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">🧠</span>
                    <span>暂无记忆</span>
                    <span className="empty-sub">搜索或保存新的记忆</span>
                  </div>
                ) : (
                  memoryResults.map((memory, index) => (
                    <div key={index} className="memory-item">
                      <div className="memory-content">{memory.content}</div>
                      <div className="memory-meta">
                        <span className="memory-type">{memory.type}</span>
                        <span className="memory-time">{new Date(memory.timestamp * 1000).toLocaleString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div className="memory-save-form">
                <textarea 
                  className="mcp-input" 
                  placeholder="输入要保存的记忆..." 
                  value={memorySaveContent} 
                  onChange={(e) => setMemorySaveContent(e.target.value)} 
                  rows={3}
                />
                <button className="mcp-connect-btn" onClick={saveMemory}>保存记忆</button>
              </div>
            </div>
          )}
        </div>
        <div className="sidebar-footer">
          <button
            className="icon-btn settings-btn"
            onClick={() => {
              const next = !settingsOpen;
              setSettingsOpen(next);
            }}
            title="设置"
          >
            <Icons.Settings />
          </button>
          {settingsOpen && (
            <>
              <div className="settings-backdrop" onClick={() => setSettingsOpen(false)} />
              <div className="settings-popover" onClick={(e) => e.stopPropagation()}>
                <div className="settings-header">
                  <div className="settings-title">设置中心</div>
                  <button className="settings-close-btn" onClick={() => setSettingsOpen(false)}>
                    ×
                  </button>
                </div>
                <div className="settings-section">
                  <div className="settings-section-title">通用设置</div>
                  <label className="settings-row">
                    <span>KPI 模式</span>
                    <input
                      type="checkbox"
                      checked={kpiMode}
                      onChange={(e) => {
                        setKpiMode(e.target.checked);
                      }}
                    />
                  </label>
                  <label className="settings-row">
                    <span>语言</span>
                    <select
                      value={language}
                      onChange={(e) => {
                        setLanguage(e.target.value);
                      }}
                    >
                      <option value="zh-CN">中文</option>
                      <option value="en-US">English</option>
                      <option value="ja-JP">日本語</option>
                    </select>
                  </label>
                  <label className="settings-row">
                    <span>显示统计卡</span>
                    <input
                      type="checkbox"
                      checked={showTokenStats}
                      onChange={(e) => setShowTokenStats(e.target.checked)}
                    />
                  </label>
                </div>
                <div className="settings-section">
                  <div className="settings-section-title">API 配置</div>
                  <button className="api-config-btn" onClick={() => setApiConfigModalOpen(true)}>
                    <span className="btn-icon">⚙️</span>
                    <span>管理 API 供应商</span>
                  </button>
                  <button className="api-config-btn" onClick={handleSelfEvolve} style={{marginTop: 8}}>
                    <span className="btn-icon">↻</span>
                    <span>运行自我进化</span>
                  </button>
                  <input
                    className="mcp-input"
                    style={{marginTop: 8}}
                    value={selfEvolutionGoal}
                    onChange={(e) => setSelfEvolutionGoal(e.target.value)}
                    placeholder="自我进化目标，例如：优化技能、记忆和 MCP 集成"
                  />
                  <label className="settings-row api-config">
                    <span>服务器 Token</span>
                    <input
                      type="password"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="EVOLVER_SERVER_TOKEN"
                      autoComplete="off"
                    />
                  </label>
                  {apiConfigSummary && <div className="settings-hint">{apiConfigSummary}</div>}
                </div>
              </div>
            </>
          )}
        </div>
      </aside>

      <main className="main-content">
        <div className="top-bar">
          <div className="breadcrumb">
            <span className="breadcrumb-item">当前智能体: {selectedAgent.name}</span>
          </div>
          <div className="top-actions">
            <button className="icon-btn" onClick={refreshServerStatus} title="刷新服务器状态">
              <Icons.Refresh />
            </button>
            <button
              className="icon-btn"
              onClick={async () => {
                try {
                  setIsLoading(true);
                  const agents = await rpcCall<Array<{ id: string; name: string; description?: string }>>(
                    { method: "get_agents" },
                    authToken
                  );
                  if (Array.isArray(agents) && agents.length > 0) {
                    const normalized = agents.map((item) => ({
                      id: item.id,
                      name: item.name,
                      desc: item.description ?? ""
                    }));
                    setAgentOptions(normalized);
                    setSelectedAgentId(normalized[0].id);
                    showToast("success", "智能体列表已更新");
                  }
                } catch (e) {
                  setOutput(String(e));
                  showToast("error", `刷新智能体失败: ${String(e)}`);
                } finally {
                  setIsLoading(false);
                }
              }}
              title="刷新智能体"
            >
              <Icons.Refresh />
            </button>
            <button 
              className="icon-btn" 
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              title={theme === "light" ? "切换到深色模式" : "切换到浅色模式"}
            >
              {theme === "light" ? <Icons.Moon /> : <Icons.Sun />}
            </button>
          </div>
        </div>

        <div className="messages-container">
          {chatLines.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><Icons.MessageSquare /></div>
              <div className="empty-title">开始对话</div>
              <div className="empty-description">选择一个智能体并创建会话，开始与AI交流</div>
            </div>
          ) : (
            chatLines.map((line, idx) => (
              <div key={line.id || idx} className={`message ${line.role}`}>
                <div className="message-avatar">{line.role === "assistant" ? <Icons.Bot /> : <Icons.User />}</div>
                <div className="message-content">
                  <div className="message-bubble">{line.content}</div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-bar">
          <div className="chat-bar-top" ref={barRef}>
            <div className={`model-selector ${projectModalOpen ? "open" : ""}`} onClick={() => setProjectModalOpen((v) => !v)}>
              <div className="model-icon">P</div>
              <div className="model-info">
                <div className="model-name">{selectedProjectId}</div>
                <div className="model-provider">项目</div>
              </div>
              <span className="model-arrow"><Icons.ChevronDown /></span>
            </div>
            <div className={`model-selector ${modelOpen ? "open" : ""}`} onClick={() => setModelOpen((v) => !v)}>
              <div className="model-icon">C</div>
              <div className="model-info">
                <div className="model-name">{selectedModel}</div>
                <div className="model-provider">模型选择</div>
              </div>
              <span className="model-arrow"><Icons.ChevronDown /></span>
            </div>
            <div className={`model-selector ${agentOpen ? "open" : ""}`} onClick={() => setAgentOpen((v) => !v)}>
              <div className="skill-icon default" style={{width: 24, height: 24, fontSize: 12}}>{selectedAgent.name[0]}</div>
              <div className="model-info">
                <div className="model-name">{selectedAgent.name}</div>
                <div className="model-provider">智能体</div>
              </div>
              <span className="model-arrow"><Icons.ChevronDown /></span>
            </div>
            <button className="create-session-btn" onClick={createSession} disabled={isLoading}>
              {isLoading ? <div className="loading"></div> : "创建会话"}
            </button>
          </div>
          {modelOpen && (
            <div className="dropdown">
              <div className="dropdown-header">选择模型</div>
              {["GLM-5", "Claude 4 Sonnet", "Claude 4 Opus", "GPT-4o", "GPT-4 Turbo"].map((item) => (
                <button key={item} className={`dropdown-item ${selectedModel === item ? "active" : ""}`} onClick={() => { setSelectedModel(item); setModelOpen(false); showToast("success", `已切换到模型: ${item}`); }}>
                  <div style={{width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600}}>
                    {item.includes("GLM") ? "G" : item.includes("Claude") ? "C" : "O"}
                  </div>
                  <div style={{flex: 1}}>
                    <div style={{fontSize: 14, fontWeight: 500}}>{item}</div>
                    <div style={{fontSize: 12, color: 'var(--text-tertiary)'}}>{item.includes("GLM") ? "Zhipu AI" : item.includes("Claude") ? "Anthropic" : "OpenAI"}</div>
                  </div>
                  {selectedModel === item && <span style={{color: 'var(--accent-primary)'}}>✓</span>}
                </button>
              ))}
              {customModels.length > 0 && (
                <>
                  <div className="dropdown-divider"></div>
                  <div className="dropdown-header">自定义模型</div>
                  {customModels.map((item) => (
                    <button key={item} className={`dropdown-item ${selectedModel === item ? "active" : ""}`} onClick={() => { setSelectedModel(item); setModelOpen(false); showToast("success", `已切换到模型: ${item}`); }}>
                      <div style={{width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600}}>
                        C
                      </div>
                      <div style={{flex: 1}}>
                        <div style={{fontSize: 14, fontWeight: 500}}>{item}</div>
                        <div style={{fontSize: 12, color: 'var(--text-tertiary)'}}>自定义 API</div>
                      </div>
                      {selectedModel === item && <span style={{color: 'var(--accent-primary)'}}>✓</span>}
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
          {agentOpen && (
            <div className="dropdown">
              <div className="dropdown-header">选择智能体</div>
              {agentOptions.map((agent) => (
                <button key={agent.id} className={`dropdown-item ${selectedAgentId === agent.id ? "active" : ""}`} onClick={() => { setSelectedAgentId(agent.id); setAgentOpen(false); showToast("success", `已切换到智能体: ${agent.name}`); }}>
                  <div className={`skill-icon ${agent.id}`} style={{width: 32, height: 32, fontSize: 14}}>{agent.id === "code" ? "C" : agent.id === "debug" ? "D" : agent.id === "design" ? "U" : "AI"}</div>
                  <div style={{flex: 1}}>
                    <div style={{fontSize: 14, fontWeight: 500}}>{agent.name}</div>
                    <div style={{fontSize: 12, color: 'var(--text-tertiary)'}}>{agent.desc}</div>
                  </div>
                  {selectedAgentId === agent.id && <span style={{color: 'var(--accent-primary)'}}>✓</span>}
                </button>
              ))}
            </div>
          )}
          {projectModalOpen && (
            <div className="dropdown">
              <div className="dropdown-header">选择项目</div>
              {projects.map((project) => (
                <button key={project.project_id} className={`dropdown-item ${selectedProjectId === project.project_id ? "active" : ""}`} onClick={() => { setActiveProject(project.project_id); setProjectModalOpen(false); }}>
                  <div style={{width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600}}>
                    P
                  </div>
                  <div style={{flex: 1}}>
                    <div style={{fontSize: 14, fontWeight: 500}}>{project.name}</div>
                    <div style={{fontSize: 12, color: 'var(--text-tertiary)'}}>{project.description || "无描述"}</div>
                  </div>
                  {selectedProjectId === project.project_id && <span style={{color: 'var(--accent-primary)'}}>✓</span>}
                </button>
              ))}
              <div className="dropdown-divider"></div>
              <div className="dropdown-header">创建新项目</div>
              <div className="dropdown-form">
                <input 
                  className="dropdown-input" 
                  placeholder="项目名称" 
                  value={newProjectName} 
                  onChange={(e) => setNewProjectName(e.target.value)} 
                />
                <input 
                  className="dropdown-input" 
                  placeholder="项目描述 (可选)" 
                  value={newProjectDescription} 
                  onChange={(e) => setNewProjectDescription(e.target.value)} 
                />
                <button className="dropdown-btn" onClick={createProject} disabled={!newProjectName.trim()}>
                  创建项目
                </button>
              </div>
            </div>
          )}
          <div className="chat-input-container">
            <div className="chat-input-wrapper">
              <textarea
                className="chat-input"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入消息... (按Enter发送，Shift+Enter换行)"
                rows={1}
                disabled={isLoading}
              />
            </div>
            <button className="send-btn" onClick={sendChat} disabled={isLoading || !sessionId || !message.trim()}>
              {isLoading ? <div className="loading"></div> : <Icons.Send />}
            </button>
          </div>
          {output && <pre className="debug-output">{output}</pre>}
        </div>
      </main>

      <aside className="right-panel">
        <div className="panel-header">
          <span className="panel-title">工具面板</span>
        </div>
        <div className="panel-tabs">
          <button className={`panel-tab ${rightTab === "terminal" ? "active" : ""}`} onClick={() => setRightTab("terminal")}>
            <Icons.Terminal /> 终端
          </button>
          <button className={`panel-tab ${rightTab === "files" ? "active" : ""}`} onClick={() => setRightTab("files")}>
            <Icons.Folder /> 文件
          </button>
          <button className={`panel-tab ${rightTab === "status" ? "active" : ""}`} onClick={() => setRightTab("status")}>
            <Icons.Activity /> 状态
          </button>
        </div>
        <div className="panel-content">
          {rightTab === "terminal" ? (
            <div className="terminal-container">
              {recentFailures.length > 0 && (
                <div className="terminal-output-section">
                  <div className="output-header">最近失败记录</div>
                  <div className="terminal-log-container" style={{maxHeight: 160}}>
                    {recentFailures.slice().reverse().map((item, idx) => (
                      <div key={`${item.timestamp}-${idx}`} className="terminal-log-entry error">
                        <span className="log-time">{new Date(item.timestamp * 1000).toLocaleTimeString("zh-CN", { hour12: false })}</span>
                        <span className="log-message">{item.reason}</span>
                        <span className="log-details">{item.agent_id} · {item.session_id}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {selfEvolutionHistory.length > 0 && (
                <div className="terminal-output-section">
                  <div className="output-header">自我进化记录</div>
                  <div className="terminal-log-container" style={{maxHeight: 180}}>
                    {selfEvolutionHistory.slice().reverse().map((item, idx) => (
                      <div key={`${item.timestamp}-${idx}`} className="terminal-log-entry system">
                        <span className="log-time">{new Date(item.timestamp * 1000).toLocaleTimeString("zh-CN", { hour12: false })}</span>
                        <span className="log-message">{item.goal}</span>
                        <span className="log-details">{item.recommendations.map((rec) => `${rec.area}:${rec.action}`).join(" | ")}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {workItems.length > 0 && (
                <div className="terminal-output-section">
                  <div className="output-header">待办 / 工单</div>
                  <div className="terminal-log-container" style={{maxHeight: 180}}>
                    {workItems.slice().reverse().map((item) => (
                      <div key={item.id} className="terminal-log-entry info">
                        <span className="log-time">{new Date(item.created_at * 1000).toLocaleTimeString("zh-CN", { hour12: false })}</span>
                        <span className="log-message">{item.title}</span>
                        <span className="log-details">{item.status} · {item.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="terminal-header">
                <div className="terminal-dots">
                  <span className={`dot ${isLoading ? "blink" : ""}`} style={{background: isLoading ? "#e85d04" : "#ff5f57"}} />
                  <span className="dot" style={{background: "#febc2e"}} />
                  <span className="dot" style={{background: "#28c840"}} />
                </div>
                <div className="terminal-title">任务进程</div>
                <div className="terminal-actions">
                  <button className="tiny-btn" onClick={() => setTaskLogs([])}>清空</button>
                  <button className="tiny-btn" onClick={() => {
                    const text = taskLogs.map(l => `[${l.timestamp}] [${l.type.toUpperCase()}] ${l.message}${l.details ? ` - ${l.details}` : ''}`).join('\n');
                    navigator.clipboard.writeText(text);
                    showToast("success", "日志已复制");
                  }}>复制</button>
                </div>
              </div>
              <div className="terminal-log-container">
                {taskLogs.length === 0 ? (
                  <div className="terminal-empty">
                    <Icons.Terminal />
                    <span>暂无任务记录</span>
                    <span className="subtle">操作后将在此显示进程日志</span>
                  </div>
                ) : (
                  taskLogs.map((log) => (
                    <div key={log.id} className={`terminal-log-entry ${log.type}`}>
                      <span className="log-time">{log.timestamp}</span>
                      <span className={`log-type ${log.type}`}>{log.type === "info" ? "ℹ" : log.type === "success" ? "✓" : log.type === "error" ? "✗" : log.type === "warning" ? "⚠" : "●"}</span>
                      <span className="log-message">{log.message}</span>
                      {log.details && <span className="log-details">{log.details}</span>}
                    </div>
                  ))
                )}
              </div>
              <div className="terminal-controls" style={{ flexDirection: "column", alignItems: "stretch", gap: 8 }}>
                <label className="form-label" style={{ fontSize: 12 }}>本地命令（后端进程权限）</label>
                <textarea
                  className="form-input"
                  style={{ minHeight: 56, fontFamily: "ui-monospace, monospace", fontSize: 12 }}
                  value={shellCmd}
                  onChange={(e) => setShellCmd(e.target.value)}
                  placeholder="例如: dir&#10;或: python --version"
                  disabled={isLoading}
                />
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button className="toolbar-btn panel-btn" type="button" onClick={runShellCommand} disabled={isLoading || !shellCmd.trim()}>
                    运行
                  </button>
                  <button className="toolbar-btn panel-btn" type="button" onClick={() => setShellCmd("")} disabled={isLoading}>
                    清空
                  </button>
                </div>
                <div style={{ fontSize: 11, opacity: 0.75 }}>
                  说明：与系统终端相同权限，请谨慎使用。测试打开浏览器可执行: <code style={{ fontSize: 11 }}>start https://www.baidu.com</code>（Windows）
                </div>
              </div>
              <div className="terminal-controls">
                <button className="toolbar-btn panel-btn" onClick={startServer} disabled={isLoading}>
                  {isLoading ? <div className="loading"></div> : "▶ 启动后端"}
                </button>
                <button className="toolbar-btn panel-btn" onClick={stopServer} disabled={isLoading}>
                  {isLoading ? <div className="loading"></div> : "■ 停止后端"}
                </button>
                <button className="toolbar-btn panel-btn" onClick={() => { refreshServerStatus(); addTaskLog("system", "手动刷新服务器状态"); }} disabled={isLoading}>
                  ↻ 刷新状态
                </button>
              </div>
              {output && (
                <div className="terminal-output-section">
                  <div className="output-header">输出</div>
                  <pre className="debug-output-terminal">{output}</pre>
                </div>
              )}
            </div>
          ) : rightTab === "files" ? (
            <div style={{ padding: "10px", overflow: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ fontWeight: "bold" }}>本地文件预览</div>
              {previewFilePath ? (
                <>
                  <div style={{ fontSize: 11, opacity: 0.8, wordBreak: "break-all" }}>{previewFilePath}</div>
                  <pre
                    style={{
                      flex: 1,
                      minHeight: 120,
                      maxHeight: 360,
                      overflow: "auto",
                      fontSize: 12,
                      padding: 8,
                      background: "var(--panel-bg, rgba(0,0,0,0.04))",
                      borderRadius: 6
                    }}
                  >
                    {previewFileContent}
                  </pre>
                </>
              ) : (
                <div className="terminal-empty" style={{ padding: 16 }}>
                  <Icons.File />
                  <span>在左侧选择目录并点击文件即可预览</span>
                </div>
              )}
              <div style={{ fontWeight: "bold", marginTop: 8 }}>快捷打开项目目录</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {[
                  ["evolver", "技能 / evolver"],
                  ["frontend", "前端"],
                  ["monitoring", "监控"]
                ].map(([rel, label]) => (
                  <button
                    key={rel}
                    className="toolbar-btn panel-btn"
                    type="button"
                    style={{ justifyContent: "flex-start" }}
                    onClick={() => {
                      showToast("info", `请在资源管理器中打开仓库根下的文件夹：${rel}`);
                    }}
                  >
                    <Icons.Folder /> {label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="status-item">
                <div className="status-label">
                  <span className={`status-dot ${serverStatus === "running" ? "" : serverStatus.includes("error") ? "offline" : "warning"}`} />
                  服务状态
                </div>
                <span className="status-value">{serverStatus}</span>
              </div>
              <div className="status-item">
                <div className="status-label">
                  <span className="status-dot" />
                  当前智能体
                </div>
                <span className="status-value">{selectedAgent.name}</span>
              </div>
              <div className="status-item">
                <div className="status-label">
                  <span className="status-dot" />
                  当前模型
                </div>
                <span className="status-value">{selectedModel}</span>
              </div>
              <div className="status-item">
                <div className="status-label">
                  <span className="status-dot" />
                  会话ID
                </div>
                <span className="status-value">{sessionId || "未创建"}</span>
              </div>
              {showTokenStats && (
                <div className="token-stats">
                  <div className="token-stat">
                    <div className="token-value">{chatLines.length}</div>
                    <div className="token-label">消息数</div>
                  </div>
                  <div className="token-stat">
                    <div className="token-value">{sessionId ? "1" : "0"}</div>
                    <div className="token-label">会话</div>
                  </div>
                  <div className="token-stat">
                    <div className="token-value">{selectedModel.includes("Claude") ? "A" : "O"}</div>
                    <div className="token-label">模型</div>
                  </div>
                  <div className="token-stat">
                    <div className="token-value">{kpiMode ? "ON" : "OFF"}</div>
                    <div className="token-label">KPI</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>

      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.type}`}>{toast.message}</div>
      ))}
      {apiConfigModalOpen && (
        <div className="modal-overlay" onClick={() => setApiConfigModalOpen(false)}>
          <div className="api-config-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">API 供应商管理</div>
              <button className="modal-close" onClick={() => setApiConfigModalOpen(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="provider-selector">
                <label className="form-label">供应商</label>
                <select
                  className="form-select"
                  value={modelConfig.provider}
                  onChange={(e) => setModelConfig({ ...modelConfig, provider: e.target.value })}
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="google">Google AI</option>
                  <option value="deepseek">DeepSeek</option>
                  <option value="zhipu">智谱 AI (GLM)</option>
                  <option value="custom">自定义 API</option>
                </select>
              </div>
              <div className="api-key-input">
                <label className="form-label">API Key</label>
                <div className="input-with-toggle">
                  <input
                    type="password"
                    className="form-input"
                    value={modelConfig.apiKey}
                    onChange={(e) => setModelConfig({ ...modelConfig, apiKey: e.target.value })}
                    placeholder={
                      modelConfig.provider === "openai" ? "sk-..." : 
                      modelConfig.provider === "anthropic" ? "sk-ant-..." : 
                      modelConfig.provider === "google" ? "AIza..." : 
                      modelConfig.provider === "deepseek" ? "sk-..." : 
                      modelConfig.provider === "zhipu" ? "sk-..." : 
                      "API Key..."
                    }
                  />
                  <button className="toggle-btn" onClick={(e) => {
                    e.preventDefault();
                    const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                    if (input) input.type = input.type === 'password' ? 'text' : 'password';
                  }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  </button>
                </div>
              </div>
              {modelConfig.provider === "custom" && (
                <div className="endpoint-input">
                  <label className="form-label">端点地址</label>
                  <input
                    type="text"
                    className="form-input"
                    value={modelConfig.customEndpoint}
                    onChange={(e) => setModelConfig({ ...modelConfig, customEndpoint: e.target.value })}
                    placeholder="https://api.example.com/v1/chat/completions"
                  />
                </div>
              )}
              <div className="model-selector">
                <label className="form-label">模型名称</label>
                <input
                  type="text"
                  className="form-input"
                  value={modelConfig.modelName}
                  onChange={(e) => {
                    console.log('Input value:', e.target.value);
                    setModelConfig({ ...modelConfig, modelName: e.target.value });
                  }}
                  placeholder="输入模型名称"
                  style={{ position: 'relative', zIndex: 100 }}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setApiConfigModalOpen(false)}>取消</button>
              <button className="btn-secondary" type="button" onClick={() => validateApiConfig()} disabled={isLoading}>
                验证连接
              </button>
              <button className="btn-primary" onClick={async () => {
                const field = modelConfig.provider === "openai" ? "openaiApiKey" : 
                              modelConfig.provider === "anthropic" ? "anthropicApiKey" : 
                              modelConfig.provider === "google" ? "googleApiKey" : 
                              modelConfig.provider === "deepseek" ? "deepseekApiKey" : 
                              modelConfig.provider === "zhipu" ? "customApiKey" : "customApiKey";
                const ep = endpointForProvider(modelConfig.provider, modelConfig.customEndpoint);
                setApiConfig({ 
                  ...apiConfig, 
                  [field]: modelConfig.apiKey,
                  customEndpoint: modelConfig.provider === "custom" ? modelConfig.customEndpoint : apiConfig.customEndpoint,
                  modelName: modelConfig.modelName
                });
                
                // 如果是自定义API，将模型添加到自定义模型列表
                if (modelConfig.provider === "custom" && modelConfig.modelName) {
                  setCustomModels(prev => {
                    if (!prev.includes(modelConfig.modelName)) {
                      return [...prev, modelConfig.modelName];
                    }
                    return prev;
                  });
                }
                
                // 发送API配置到后端
                try {
                  const result = await rpcCall<{ success: boolean; message?: string; error?: string }>(
                    { 
                      method: "update_api_config", 
                      params: { 
                        config: {
                          [modelConfig.provider]: {
                            api_key: modelConfig.apiKey,
                            model_name: modelConfig.modelName,
                            ...(ep ? { endpoint: ep } : {})
                          }
                        }
                      } 
                    }, 
                    authToken
                  );
                  if (!result?.success) {
                    throw new Error(result?.error || result?.message || "保存失败");
                  }
                } catch (e) {
                  const errorMessage = e instanceof Error ? e.message : String(e);
                  console.error("保存API配置到后端失败:", e);
                  showToast("error", `API配置保存失败: ${errorMessage}`);
                  addTaskLog("error", `API配置保存失败`, errorMessage);
                  setOutput(`API配置保存失败: ${errorMessage}`);
                  return;
                }
                
                setApiConfigSummary(`${modelConfig.provider} 已保存，当前模型 ${modelConfig.modelName || "未选择"}`);
                setApiConfigModalOpen(false);
                showToast("success", `${modelConfig.provider} 配置已保存`);
              }}>保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}