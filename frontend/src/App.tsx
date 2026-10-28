import { useEffect, useState } from "react";
import { getHealth } from "./api";
import Chat from "./Chat";
import DocumentPanel from "./DocumentPanel";

export default function App() {
  const [selected, setSelected] = useState<string[]>([]);
  const [llmOk, setLlmOk] = useState(true);

  useEffect(() => {
    getHealth()
      .then((h) => setLlmOk(h.llm_configured))
      .catch(() => setLlmOk(false));
  }, []);

  return (
    <div className="app">
      <DocumentPanel selected={selected} onSelectedChange={setSelected} />
      <div className="main">
        {!llmOk && (
          <div className="banner">
            Backend unreachable or the LLM API key is not set. Set it in backend/.env and restart.
          </div>
        )}
        <Chat sources={selected} />
      </div>
    </div>
  );
}
