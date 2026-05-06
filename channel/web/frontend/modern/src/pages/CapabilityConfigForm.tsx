import { Form, Input, Select, Space, Switch } from 'antd';
import type { FormInstance } from 'antd';
import type { CapabilityConfigItem, CapabilityProviderOption } from '../types';
import {
  apiKeyKeepValueExtra,
  findDefaultBaseForProvider,
  findFirstProviderForCapability,
  supportsImageSizeField,
  supportsVoiceField,
} from './modelConfigShared';

interface SelectOption {
  label: string;
  value: string;
}

interface CapabilityConfigFormProps {
  form: FormInstance;
  editing: CapabilityConfigItem | null;
  capabilityOptions: SelectOption[];
  capabilityProviderOptions: SelectOption[];
  effectiveCapabilityProviders: CapabilityProviderOption[];
  selectedCapability?: string;
  selectedCapabilityProvider?: CapabilityProviderOption;
  idPrefix: string;
  scopeLabel: string;
  showPublicToggle?: boolean;
}

export function CapabilityConfigForm({
  form,
  editing,
  capabilityOptions,
  capabilityProviderOptions,
  effectiveCapabilityProviders,
  selectedCapability,
  selectedCapabilityProvider,
  idPrefix,
  scopeLabel,
  showPublicToggle = false,
}: CapabilityConfigFormProps) {
  return (
    <Form form={form} layout="vertical">
      <Form.Item name="capability" label="能力类型" rules={[{ required: true }]}>
        <Select
          options={capabilityOptions}
          showSearch
          aria-label="能力类型"
          onChange={(value) => {
            const provider = findFirstProviderForCapability(effectiveCapabilityProviders, String(value));
            form.setFieldsValue({
              provider,
              api_base: findDefaultBaseForProvider(effectiveCapabilityProviders, provider),
              voice: '',
              image_size: '',
            });
          }}
        />
      </Form.Item>
      <Form.Item name="provider" label="厂商" rules={[{ required: true }]}>
        <Select
          options={capabilityProviderOptions}
          showSearch
          aria-label="厂商"
          onChange={(value) => form.setFieldValue('api_base', findDefaultBaseForProvider(effectiveCapabilityProviders, String(value)))}
        />
      </Form.Item>
      <Form.Item name="model_name" label="Model" rules={[{ required: true }]}>
        <Input aria-label="Model" />
      </Form.Item>
      <Form.Item
        name="api_base"
        label={selectedCapabilityProvider?.custom ? 'Base URL（自定义厂商必填）' : 'Base URL'}
        rules={selectedCapabilityProvider?.custom ? [{ required: true, message: '请输入 Base URL' }] : []}
      >
        <Input aria-label="Base URL" />
      </Form.Item>
      <Form.Item
        name="api_key"
        label="API Key"
        extra={apiKeyKeepValueExtra(editing)}
      >
        <Input.Password autoComplete="new-password" aria-label="API Key" />
      </Form.Item>
      {supportsVoiceField(selectedCapability) ? (
        <Form.Item name="voice" label="Voice / 音色">
          <Input aria-label="Voice / 音色" />
        </Form.Item>
      ) : null}
      {supportsImageSizeField(selectedCapability) ? (
        <Form.Item name="image_size" label="图片尺寸">
          <Input aria-label="图片尺寸" placeholder="1024x1024" />
        </Form.Item>
      ) : null}
      <Space size={32}>
        <Form.Item name="enabled" label="启用" htmlFor={`${idPrefix}-enabled`} valuePropName="checked">
          <Switch id={`${idPrefix}-enabled`} aria-label={`启用${scopeLabel}`} />
        </Form.Item>
        {showPublicToggle ? (
          <Form.Item name="is_public" label="租户可见" htmlFor={`${idPrefix}-public`} valuePropName="checked">
            <Switch id={`${idPrefix}-public`} aria-label="租户可见" />
          </Form.Item>
        ) : null}
        <Form.Item name="is_default" label="默认" htmlFor={`${idPrefix}-default`} valuePropName="checked">
          <Switch id={`${idPrefix}-default`} aria-label={`默认${scopeLabel}`} />
        </Form.Item>
      </Space>
    </Form>
  );
}
