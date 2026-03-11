import { useState, useRef } from "react";
import { API } from "../api";

function UploadFile() {

  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [dragging, setDragging] = useState(false);

  const fileInputRef = useRef(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const uploadFile = async () => {

    const formData = new FormData();
    formData.append("file", file);

    try {

      const response = await API.post("/upload", formData);

      const id = response.data.task_id;

      setTaskId(id);
      setStatus("processing");
      setUploadMessage("✔ File uploaded successfully!");

      startStatusPolling(id);

    } catch (error) {

      console.error(error);
      alert("Upload failed");

    }

  };

  const startStatusPolling = (id) => {

    const interval = setInterval(async () => {

      try {

        const response = await API.get(`/status/${id}`);

        const taskStatus = response.data.status;

        setStatus(taskStatus);

        if (taskStatus === "completed") {

          setDownloadUrl(response.data.output_file);
          setFile(null);
          setUploadMessage("");   // clear upload message

          clearInterval(interval);

        }

      } catch (error) {

        console.error(error);

      }

    }, 3000); // check every 3 seconds

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

  if (fileInputRef.current) {
    fileInputRef.current.value = "";
  }
};
  

const resetForm = () => {
  setFile(null);
  setStatus("");
  setDownloadUrl("");
  setTaskId("");

  if (fileInputRef.current) {
    fileInputRef.current.value = "";
  }
};

  return (
  <div className="space-y-4">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
        ${dragging ? "border-blue-500 bg-blue-50 scale-[1.02]" : "border-gray-300 bg-gray-50 hover:bg-gray-100"}`}
      >

      <p className="text-gray-600">
        <div className="text-4xl mb-2">📤</div>
        {dragging ? "Drop your Excel file here" : "Drag & Drop Excel file here"}
      </p>

        <p className="text-gray-400 text-sm">
          or select a file
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx"
          onChange={(e) => {
            const selectedFile = e.target.files[0];

            if (selectedFile && !selectedFile.name.endsWith(".xlsx")) {
              setErrorMessage("❌ Only Excel (.xlsx) files are allowed");
              setFile(null);
              return;
            }

            setErrorMessage("");
            setFile(selectedFile);
          }}
          className="mt-3"
        />

        {file && (
          <div className="mt-3 flex justify-center items-center gap-3">
            <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm hover:scale-105 transition">
              📄 {file.name}
            </span>

            <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm hover:scale-105 transition">
              📦 {(file.size / 1024).toFixed(1)} KB
            </span>{" "}

          </div>
        )}

      </div>

    {uploadMessage && (
      <div className="text-green-600 text-sm font-medium text-center">
        {uploadMessage}
      </div>
    )}

    {taskId && (
      <div className="text-sm text-gray-500 text-center">
        Task ID: <span className="font-medium">{taskId}</span>
      </div>
    )}

    {errorMessage && (
      <div className="text-red-500 text-sm text-center">
        {errorMessage}
      </div>
    )}

    <div className="flex gap-3">

      <button
        onClick={uploadFile}
        disabled={!file || status === "processing"}
        className="flex-1 bg-blue-600 text-white py-2 rounded-lg shadow hover:bg-blue-700 hover:shadow-md transition disabled:bg-gray-400 transition"
      >
        {status === "processing" ? "Processing..." : "Upload File"}
      </button>

      <button
        onClick={removeFile}
        disabled={!file || status === "processing"}
        className="bg-red-500 text-white px-4 py-2 rounded-lg shadow hover:bg-red-600 hover:shadow-md transition disabled:bg-gray-300"
      >
        Remove
      </button>

    </div>

    {status === "processing" && (
      <div className="text-center space-y-3 bg-gray-50 p-4 rounded-lg">

        <div className="flex justify-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>

        <div className="text-yellow-600 font-medium">
          Validating NPIs... please wait
        </div>

      </div>
    )}

    {status === "completed" && (
  <div className="text-center space-y-3">

    <div className="text-green-600 font-semibold">
      ✔ Processing Completed
    </div>

    <div className="flex justify-center gap-3">

      <a
        href={`http://127.0.0.1:8000/download/${downloadUrl}`}
        className="bg-green-500 text-white px-4 py-2 rounded-lg shadow hover:bg-green-700 hover:shadow-md transition"
      >
        Download
      </a>

      <button
        onClick={resetForm}
        className="bg-gray-500 text-white px-4 py-2 rounded-lg shadow hover:bg-gray-700 hover:shadow-md transition"
      >
        Reset
      </button>

    </div>

  </div>
)}

  </div>
);

}

export default UploadFile;