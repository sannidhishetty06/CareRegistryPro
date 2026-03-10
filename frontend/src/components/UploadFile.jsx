import { useState } from "react";
import { API } from "../api";

function UploadFile() {

  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [dragging, setDragging] = useState(false);

  const uploadFile = async () => {

    const formData = new FormData();
    formData.append("file", file);

    try {

      const response = await API.post("/upload", formData);

      const id = response.data.task_id;

      setTaskId(id);
      setStatus("processing");

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
          setFile(null)
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

  if (droppedFile) {
    setFile(droppedFile);
  }
};

const handleDragOver = (e) => {
  e.preventDefault();
  setDragging(true);
};

const handleDragLeave = () => {
  setDragging(false);
};
  
  return (
  <div className="space-y-4">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition
        ${dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50"}`}
      >

      <p className="text-gray-600">
        {dragging ? "Drop your Excel file here" : "Drag & Drop Excel file here"}
      </p>

        <p className="text-gray-400 text-sm">
          or select a file
        </p>

        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => setFile(e.target.files[0])}
          className="mt-3"
        />

        {file && (
          <p className="text-sm text-gray-500 mt-2">
            Selected: {file.name}
          </p>
        )}

      </div>

    <button
      onClick={uploadFile}
      disabled={!file || status === "processing"}
      className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition"
    >
      {status === "processing" ? "Processing..." : "Upload File"}
    </button>

    {status === "processing" && (
      <div className="text-center text-yellow-600 font-medium">
        Processing file... please wait
      </div>
    )}

    {status === "completed" && (
      <div className="text-center space-y-3">

        <div className="text-green-600 font-semibold">
          ✔ Processing Completed
        </div>

        <a
          href={`http://127.0.0.1:8000/download/${downloadUrl}`}
          className="inline-block bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition"
        >
          Download Output File
        </a>

      </div>
    )}

  </div>
);

}

export default UploadFile;