import { useState, useRef } from "react";
import { API } from "../api";

function UploadFile() {
  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [dragging, setDragging] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [progress, setProgress] = useState(0);

  const fileInputRef = useRef(null);

  const uploadFile = async () => {
    if (!file) {
      setErrorMessage("❌ Please select a file");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setErrorMessage("");
      setUploadMessage("📤 Uploading file...");
      setProgress(30);

      const response = await API.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      const id = response.data.task_id;
      setTaskId(id);
      setStatus("processing");
      setProgress(60);
      setUploadMessage("✅ File uploaded successfully! Processing started...");

      startStatusPolling(id);
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || "Upload failed";
      setErrorMessage(`❌ ${errorMsg}`);
      setProgress(0);
    }
  };

  const startStatusPolling = (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await API.get(`/status/${id}`);
        const taskStatus = response.data.status;

        setStatus(taskStatus);

        if (taskStatus === "processing") {
          setProgress(75);
        } else if (taskStatus === "completed") {
          setProgress(100);
          setDownloadUrl(response.data.output_file);
          setFile(null);
          setUploadMessage("✅ Processing completed!");
          clearInterval(interval);
        } else if (taskStatus === "failed") {
          setErrorMessage("❌ Processing failed. Please try again.");
          setProgress(0);
          clearInterval(interval);
        }
      } catch (error) {
        console.error(error);
      }
    }, 2000);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);

    const droppedFile = e.dataTransfer.files[0];

    if (droppedFile && !droppedFile.name.endsWith(".xlsx")) {
      setErrorMessage("❌ Only Excel (.xlsx) files are allowed");
      return;
    }

    setErrorMessage("");
    setFile(droppedFile);

    if (fileInputRef.current) {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(droppedFile);
      fileInputRef.current.files = dataTransfer.files;
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const removeFile = () => {
    setFile(null);
    setErrorMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const resetForm = () => {
    setFile(null);
    setStatus("");
    setDownloadUrl("");
    setTaskId("");
    setProgress(0);
    setUploadMessage("");
    setErrorMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-4">
      {/* FILE UPLOAD DROPZONE */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-all duration-300 cursor-pointer
        ${dragging 
          ? "border-blue-400 bg-blue-900 bg-opacity-30 scale-105 shadow-lg shadow-blue-900" 
          : "border-gray-600 bg-gray-700 bg-opacity-50 hover:bg-gray-700 hover:border-gray-500"}
        ${status === "processing" ? "opacity-50 cursor-not-allowed" : ""}`}
        onClick={() => !status && fileInputRef.current?.click()}
      >
        <div className="space-y-2">
          <div className={`text-5xl transition-transform duration-300 ${dragging ? 'scale-125' : 'scale-100'}`}>
            📤
          </div>
          <h3 className="text-lg font-semibold text-gray-100">
            {dragging ? "Drop your file here" : "Drag & Drop Excel file"}
          </h3>
          <p className="text-gray-400 text-sm">
            or click to browse your computer
          </p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx"
          onChange={(e) => {
            const selectedFile = e.target.files?.[0];

            if (selectedFile && !selectedFile.name.endsWith(".xlsx")) {
              setErrorMessage("❌ Only Excel (.xlsx) files are allowed");
              setFile(null);
              return;
            }

            setErrorMessage("");
            setFile(selectedFile || null);
          }}
          disabled={status === "processing"}
          className="hidden"
        />

        {file && (
          <div className="mt-4 pt-4 border-t border-gray-600 space-y-2 animate-in fade-in">
            <div className="flex justify-center items-center gap-3">
              <span className="bg-blue-900 bg-opacity-50 text-blue-300 px-3 py-1 rounded-full text-sm font-medium border border-blue-700">
                📄 {file.name}
              </span>
              <span className="bg-green-900 bg-opacity-50 text-green-300 px-3 py-1 rounded-full text-sm font-medium border border-green-700">
                📦 {(file.size / 1024).toFixed(1)} KB
              </span>
            </div>
          </div>
        )}
      </div>

      {/* MESSAGES */}
      {uploadMessage && (
        <div className="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-3 text-green-300 text-sm font-medium animate-in fade-in">
          {uploadMessage}
        </div>
      )}

      {errorMessage && (
        <div className="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-3 text-red-300 text-sm font-medium animate-in fade-in">
          {errorMessage}
        </div>
      )}

      {/* TASK ID */}
      {taskId && (
        <div className="bg-gray-700 rounded-lg p-3 text-center text-xs text-gray-400">
          Task ID: <span className="font-mono font-semibold text-gray-300">{taskId.substring(0, 12)}...</span>
        </div>
      )}

      {/* PROGRESS BAR */}
      {progress > 0 && status === "processing" && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-400">
            <span>Processing</span>
            <span className="font-semibold text-blue-400">{progress}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500 shadow-lg shadow-blue-900"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* ACTION BUTTONS */}
      <div className="flex gap-3">
        <button
          onClick={uploadFile}
          disabled={!file || status === "processing"}
          className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-lg shadow-lg hover:shadow-xl hover:from-blue-700 hover:to-blue-800 transition-all duration-200 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed font-semibold"
        >
          {status === "processing" ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin">⏳</span> Processing...
            </span>
          ) : (
            "Upload & Process"
          )}
        </button>

        <button
          onClick={removeFile}
          disabled={!file || status === "processing"}
          className="bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg hover:shadow-xl hover:bg-red-700 transition-all duration-200 disabled:bg-gray-600 disabled:cursor-not-allowed font-semibold"
        >
          ✕ Remove
        </button>
      </div>

      {/* PROCESSING STATE */}
      {status === "processing" && (
        <div className="bg-gray-700 bg-opacity-50 border-2 border-blue-700 rounded-lg p-6 animate-in fade-in">
          <div className="flex justify-center mb-4">
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 border-4 border-gray-600 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
            </div>
          </div>
          <div className="text-center">
            <p className="text-blue-300 font-semibold text-lg">
              🔍 Validating Providers...
            </p>
            <p className="text-blue-400 text-sm mt-1">
              This may take a few minutes depending on file size
            </p>
          </div>
        </div>
      )}

      {/* COMPLETED STATE */}
      {status === "completed" && (
        <div className="space-y-4 animate-in fade-in">
          {/* SUCCESS MESSAGE */}
          <div className="bg-gradient-to-r from-green-900 from-opacity-50 to-emerald-900 to-opacity-50 border-2 border-green-700 rounded-lg p-6 text-center">
            <div className="text-4xl mb-2">✨</div>
            <p className="text-green-300 font-bold text-xl">
              Processing Completed Successfully!
            </p>
            <p className="text-green-400 text-sm mt-1">
              Your results are ready to download
            </p>
          </div>

          {/* ACTION BUTTONS */}
          <div className="flex gap-3">
            <a
              href={`http://127.0.0.1:8000/download/${downloadUrl}`}
              download
              className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white py-3 rounded-lg shadow-lg hover:shadow-xl hover:from-green-700 hover:to-emerald-700 transition-all duration-200 font-semibold text-center"
            >
              📥 Download Results
            </a>

            <button
              onClick={resetForm}
              className="bg-gray-600 text-white px-6 py-3 rounded-lg shadow-lg hover:shadow-lg hover:bg-gray-700 transition-all duration-200 font-semibold"
            >
              ⟲ Process Another
            </button>
          </div>
        </div>
      )}

      {/* FAILED STATE */}
      {status === "failed" && (
        <div className="bg-red-900 bg-opacity-30 border-2 border-red-700 rounded-lg p-6 animate-in fade-in space-y-4">
          <div className="text-center">
            <div className="text-4xl mb-2">⚠️</div>
            <p className="text-red-300 font-bold text-lg">
              Processing Failed
            </p>
            <p className="text-red-400 text-sm mt-1">
              Something went wrong. Please check your file and try again.
            </p>
          </div>
          <button
            onClick={resetForm}
            className="w-full bg-gradient-to-r from-red-600 to-rose-600 text-white py-3 rounded-lg shadow-lg hover:shadow-xl hover:from-red-700 hover:to-rose-700 transition-all duration-200 font-semibold"
          >
            🔄 Try Again
          </button>
        </div>
      )}

      {/* HELPER TEXT */}
      {!file && !status && (
        <div className="text-xs text-gray-500 text-center pt-2">
          💡 Supported format: Excel (.xlsx) | Max file size: 10 MB 
        </div>
      )}
    </div>
  );
}

export default UploadFile;