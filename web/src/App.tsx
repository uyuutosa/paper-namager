import React, { useEffect, useState } from 'react'

type Settings = {
  provider: 'openai' | 'azure'
  model: string
  endpoint?: string
  has_key: boolean
}

export default function App() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [provider, setProvider] = useState<'openai' | 'azure'>('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [endpoint, setEndpoint] = useState('')
  const [status, setStatus] = useState('')

  async function loadSettings() {
    const res = await fetch('/api/settings')
    const data = await res.json()
    setSettings(data)
    setProvider(data.provider)
    setModel(data.model)
    setEndpoint(data.endpoint || '')
  }

  useEffect(() => {
    loadSettings().catch(console.error)
  }, [])

  async function save() {
    setStatus('Saving...')
    const res = await fetch('/api/settings/api-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey, model, endpoint })
    })
    if (res.ok) {
      setStatus('Saved.')
      setApiKey('')
      await loadSettings()
    } else {
      const t = await res.text()
      setStatus('Save failed: ' + t)
    }
  }

  async function test() {
    setStatus('Testing...')
    const res = await fetch('/api/settings/test')
    const data = await res.json()
    if (res.ok) setStatus('OK: ' + JSON.stringify(data))
    else setStatus('Failed: ' + (data.detail || JSON.stringify(data)))
  }

  return (
    <div style={{ maxWidth: 720, margin: '40px auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Paper Notes – Settings</h1>
      <p>APIキーをWebから設定できます（ローカル保存。Git管理外）。</p>

      <section style={{ border: '1px solid #ddd', padding: 16, borderRadius: 8 }}>
        <h2>AI Provider</h2>
        <label>
          Provider:&nbsp;
          <select value={provider} onChange={(e) => setProvider(e.target.value as any)}>
            <option value="openai">OpenAI</option>
            <option value="azure">Azure OpenAI</option>
          </select>
        </label>
        <div style={{ marginTop: 8 }}>
          <label>
            Model:&nbsp;
            <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4o-mini" />
          </label>
        </div>
        {provider === 'azure' && (
          <div style={{ marginTop: 8 }}>
            <label>
              Endpoint:&nbsp;
              <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="https://...azure.com/openai/..." />
            </label>
          </div>
        )}
        <div style={{ marginTop: 8 }}>
          <label>
            API Key:&nbsp;
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." />
          </label>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button onClick={save} disabled={!apiKey}>Save</button>
          <button onClick={test}>Test</button>
        </div>
        <div style={{ marginTop: 8, color: '#555' }}>{status}</div>
      </section>

      <section style={{ marginTop: 16 }}>
        <h3>Current</h3>
        {settings ? (
          <pre style={{ background: '#f7f7f7', padding: 12 }}>
            {JSON.stringify(settings, null, 2)}
          </pre>
        ) : (
          <div>Loading...</div>
        )}
      </section>
    </div>
  )
}

