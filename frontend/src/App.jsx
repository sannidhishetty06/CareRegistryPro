import UploadFile from "./components/UploadFile";

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      
      {/* BACKGROUND DECORATION */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-900 rounded-full mix-blend-screen filter blur-3xl opacity-30 animate-blob"></div>
        <div className="absolute -bottom-8 left-20 w-96 h-96 bg-purple-900 rounded-full mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-900 rounded-full mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative w-full max-w-2xl">
        {/* HEADER */}
        <div className="text-center mb-8 animate-in fade-in">
          <div className="text-5xl mb-3">🏥</div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-2">
            NPI Registry Pro
          </h1>
          <p className="text-gray-300 text-base">
            Upload an Excel file to validate provider NPI information
          </p>
          <p className="text-xs text-gray-500 mt-2">
            Powered by AI-assisted search & NPI Registry API
          </p>
        </div>

        {/* CARD */}
        <div className="bg-gray-800 shadow-2xl rounded-2xl p-8 space-y-6 border border-gray-700 backdrop-blur-sm animate-in fade-in slide-in-from-bottom-4">
          <UploadFile />
        </div>

        {/* FOOTER */}
        <div className="text-center mt-6 text-xs text-gray-500 animate-in fade-in">
          <p>
            Data sources:{" "}
            <a
              href="https://npiregistry.cms.hhs.gov/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 hover:underline font-semibold transition"
            >
              NPI Registry
            </a>
            {" | "}
            <span className="font-semibold">DuckDuckGo Search</span>
            {" | "}
            <span className="font-semibold">Groq LLM</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;