import { useState } from "react";
import { API } from "../api";

function UploadFile() {

  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");

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

          clearInterval(interval);

        }

      } catch (error) {

        console.error(error);

      }

    }, 3000); // check every 3 seconds

  };

      
  return (
  <div className="space-y-4">

    <div className="space-y-1">
      <label className="text-sm font-medium text-gray-700">
        Upload Excel File
      </label>

      <input
        type="file"
        accept=".xlsx,.xls"
        onChange={(e) => setFile(e.target.files[0])}
        className="w-full border rounded-lg p-2 cursor-pointer"
      />

      {file && (
        <p className="text-sm text-gray-500">
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