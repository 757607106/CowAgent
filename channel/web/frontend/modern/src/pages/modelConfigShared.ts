import type { CapabilityConfigItem, CapabilityProviderOption, CapabilityTypeOption } from '../types';

export interface CapabilityFormBaseValues {
  capability: string;
  provider: string;
  model_name: string;
  api_base: string;
  api_key: string;
  enabled: boolean;
  is_default: boolean;
  voice: string;
  image_size: string;
}

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
  { provider: 'dashscope', label: '通义千问 DashScope', capabilities: ['multimodal', 'image_generation'], default_api_base: 'https://dashscope.aliyuncs.com' },
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
  { provider: 'doubao', label: '豆包 Doubao', capabilities: ['multimodal', 'image_generation'], default_api_base: 'https://ark.cn-beijing.volces.com/api/v3' },
  { provider: 'claudeAPI', label: 'Claude', capabilities: ['multimodal'], default_api_base: 'https://api.anthropic.com/v1' },
  { provider: 'gemini', label: 'Gemini', capabilities: ['multimodal', 'image_generation'], default_api_base: 'https://generativelanguage.googleapis.com' },
  { provider: 'minimax', label: 'MiniMax', capabilities: ['multimodal', 'image_generation', 'text_to_speech'], default_api_base: 'https://api.minimax.io' },
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

export function providerOptionLabel(item: { label?: string; provider: string }) {
  return item.label || item.provider;
}

export function apiKeyKeepValueExtra(editing?: { api_key_set?: boolean; api_key_masked?: string } | null) {
  return editing?.api_key_set ? `留空保持 ${editing.api_key_masked || '当前值'}` : undefined;
}

export function capabilityColor(capability: string) {
  if (capability === 'image_generation') return 'magenta';
  if (capability === 'speech_to_text') return 'geekblue';
  if (capability === 'text_to_speech') return 'cyan';
  if (capability === 'multimodal') return 'purple';
  return 'blue';
}

export function supportsVoiceField(capability?: string) {
  return capability === 'text_to_speech';
}

export function supportsImageSizeField(capability?: string) {
  return capability === 'image_generation';
}

export function buildCapabilityLabels(capabilities: CapabilityTypeOption[]) {
  return Object.fromEntries(capabilities.map((item) => [item.capability, item.label]));
}

export function buildCapabilityOptions(capabilities: CapabilityTypeOption[]) {
  return capabilities.map((item) => ({ label: item.label, value: item.capability }));
}

export function getEffectiveCapabilityProviders(providers: CapabilityProviderOption[]) {
  return providers.length ? providers : capabilityProviderFallbacks;
}

export function buildCapabilityProviderOptions(
  providers: CapabilityProviderOption[],
  capability?: string,
) {
  return providers
    .filter((item) => !capability || item.capabilities.includes(capability))
    .map((item) => ({ label: providerOptionLabel(item), value: item.provider }));
}

export function findFirstProviderForCapability(
  providers: CapabilityProviderOption[],
  capability: string,
) {
  return providers.find((item) => item.capabilities.includes(capability))?.provider || 'custom';
}

export function findDefaultBaseForProvider(
  providers: CapabilityProviderOption[],
  provider: string,
) {
  return providers.find((item) => item.provider === provider)?.default_api_base || '';
}

export function buildCapabilityMetadata(values: CapabilityFormBaseValues) {
  const metadata: Record<string, unknown> = {};
  if (supportsVoiceField(values.capability) && values.voice?.trim()) metadata.voice = values.voice.trim();
  if (supportsImageSizeField(values.capability) && values.image_size?.trim()) metadata.image_size = values.image_size.trim();
  return metadata;
}

export function buildCapabilityPayload(
  values: CapabilityFormBaseValues,
  editing: CapabilityConfigItem | null,
  extra: Record<string, unknown> = {},
) {
  const payload: Record<string, unknown> = {
    capability: values.capability,
    provider: values.provider,
    model_name: values.model_name,
    display_name: values.model_name,
    api_base: values.api_base || '',
    enabled: values.enabled ?? true,
    is_default: values.is_default ?? false,
    metadata: buildCapabilityMetadata(values),
    ...extra,
  };
  if (!editing || values.api_key?.trim()) {
    payload.api_key = values.api_key || '';
  }
  return payload;
}
