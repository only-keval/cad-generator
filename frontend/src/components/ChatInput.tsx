import { useState } from 'react';

interface Props {
  disabled: boolean;
  activePrompt?: string | null;
  onSend: (prompt: string) => void;
}

export default function ChatInput({ disabled, activePrompt, onSend }: Props) {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = () => {
    if (!prompt.trim() || disabled) return;
    onSend(prompt.trim());
    setPrompt('');
  };

  return (
    <div className="chat-input">
      <textarea
        value={disabled && activePrompt ? activePrompt : prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !disabled) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Describe the 3D model you want..."
        rows={3}
        disabled={disabled}
      />
      <button
        className="btn btn-primary btn-send"
        onClick={handleSubmit}
        disabled={disabled || !prompt.trim()}
      >
        {disabled ? 'Generating...' : 'Generate'}
      </button>
    </div>
  );
}
