import UploadFile from "./components/UploadFile";

function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">

      <div className="bg-white shadow-xl rounded-xl p-8 w-[520px] space-y-4">

        <div className="text-center">
          <h1 className="text-2xl font-bold">
            NPI Processing System
          </h1>
          <p className="text-gray-500 text-sm">
            Upload an Excel file to validate provider NPI information
          </p>
        </div>

        <UploadFile />

      </div>

    </div>
  );
}

export default App;