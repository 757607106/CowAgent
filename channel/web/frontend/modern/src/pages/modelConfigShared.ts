import type { CapabilityProviderOption, CapabilityTypeOption } from '../types';

export const capabilityFallbacks: CapabilityTypeOption[] = [
  { capability: 'multimodal', label: '多模态理解' },
  { capability: 'image_generation', label: '文生图' },
  { capability: 'speech_to_text', label: '语音识别' },
  { capability: 'text_to_speech', label: '语音合成' },
  { capability: 'translation', label: '翻译' },
];

export const capabilityProviderFallbacks: CapabilityProviderOption[] = [
  {
    provider: 'openai',
    label: 'OpenAI / OpenAI 兼容',
    capabilities: ['multimodal', 'image_generation', 'speech_to_text', 'text_to_speech'],
    default_api_base: 'https://api.openai.com/v1',
  },
  {
    provider: 'custom',
    label: '自定义 OpenAI 兼容',
    capabilities: ['multimodal', 'image_generation', 'speech_to_text', 'text_to_speech', 'translation'],
    custom: true,
  },
  { provider: 'dashscope', label: '通义千问 DashScope', capabilities: ['multimodal'] },
  {
    provider: 'zhipu',
    label: '智谱 GLM / CogView',
    capabilities: ['multimodal', 'image_generation'],
    default_api_base: 'https://open.bigmodel.cn/api/paas/v4',
  },
  {
    provider: 'modelscope',
    label: '魔搭 ModelScope',
    capabilities: ['image_generation'],
    default_api_base: 'https://api-inference.modelscope.cn/v1',
  },
  { provider: 'moonshot', label: 'Kimi / Moonshot', capabilities: ['multimodal'], default_api_base: 'https://api.moonshot.cn/v1' },
  { provider: 'doubao', label: '豆包 Doubao', capabilities: ['multimodal'], default_api_base: 'https://ark.cn-beijing.volces.com/api/v3' },
  { provider: 'claudeAPI', label: 'Claude', capabilities: ['multimodal'], default_api_base: 'https://api.anthropic.com/v1' },
  { provider: 'gemini', label: 'Gemini', capabilities: ['multimodal'], default_api_base: 'https://generativelanguage.googleapis.com' },
  { provider: 'minimax', label: 'MiniMax', capabilities: ['multimodal', 'text_to_speech'], default_api_base: 'https://api.minimax.io' },
  { provider: 'linkai', label: 'LinkAI', capabilities: ['multimodal', 'image_generation', 'speech_to_text', 'text_to_speech'], default_api_base: 'https://api.link-ai.tech' },
  { provider: 'baidu', label: '百度语音/翻译', capabilities: ['speech_to_text', 'text_to_speech', 'translation'] },
  { provider: 'google', label: 'Google 语音', capabilities: ['speech_to_text', 'text_to_speech'] },
  { provider: 'azure', label: 'Azure Speech', capabilities: ['speech_to_text', 'text_to_speech'] },
  { provider: 'ali', label: '阿里云语音', capabilities: ['speech_to_text', 'text_to_speech'] },
  { provider: 'xunfei', label: '讯飞语音', capabilities: ['speech_to_text', 'text_to_speech'] },
  { provider: 'tencent', label: '腾讯云语音', capabilities: ['text_to_speech'] },
  { provider: 'edge', label: 'Edge 在线语音', capabilities: ['text_to_speech'] },
  { provider: 'elevenlabs', label: 'ElevenLabs', capabilities: ['text_to_speech'] },
  { provider: 'pytts', label: '本地 pyttsx3', capabilities: ['text_to_speech'] },
];

export function filterSelectOption(input: string, option?: { label?: unknown; value?: unknown }) {
  const keyword = input.trim().toLowerCase();
  if (!keyword) return true;
  return [option?.label, option?.value].some((value) => String(value || '').toLowerCase().includes(keyword));
}

export function providerOptionLabel(item: { label?: string; provider: string }) {
  return item.label || item.provider;
}

export function apiKeyKeepValueExtra(editing?: { api_key_set?: boolean; api_key_masked?: string } | null) {
  return editing?.api_key_set ? `留空保持 ${editing.api_key_masked || '当前值'}` : undefined;
}
