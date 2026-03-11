import UploadFile from "./components/UploadFile";

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">

      <div className="bg-white shadow-2xl rounded-2xl p-10 w-[520px] space-y-6 border">

        <div className="text-center">
          <h1 className="text-2xl font-bold">
            NPI Processing System
          </h1>
          <p className="text-gray-500 text-sm">
            Upload an Excel file to validate provider NPI information
          </p>
        </div>

        <UploadFile />

        <div className="text-xs text-gray-400 text-center pt-2">
          Supported file format: Excel (.xlsx) | Max file size: 10 MB
        </div>

      </div>

    </div>
  );
}

export default App;