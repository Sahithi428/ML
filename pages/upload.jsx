import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Info,
  Ruler,
} from "lucide-react";

import UploadBox from "../components/UploadBox";
import ImagePreview from "../components/ImagePreview";
import ErrorMessage from "../components/ErrorMessage";

import { validateImage } from "../utils/validators";
import { useProject } from "../context/ProjectContext";

function Upload() {
  const { project, updateProject } = useProject();

  const [file, setFile] = useState(project.image || null);
  const [error, setError] = useState("");

  const handleFileSelect = (selectedFile) => {
    const validationError = validateImage(selectedFile);

    if (validationError) {
      setError(validationError);
      return;
    }

    setError("");
    setFile(selectedFile);

    updateProject({
      image: selectedFile,
      imagePreview: URL.createObjectURL(selectedFile),
    });
  };

  const handleRemove = () => {
    setFile(null);

    updateProject({
      image: null,
      imagePreview: null,
    });
  };

  return (
    <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-14">

      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition"
      >
        <ArrowLeft size={16} />
        Back to Home
      </Link>

      <div className="mt-10 max-w-3xl">

        <p className="text-sm font-semibold uppercase tracking-widest text-blue-400">
          Step 1
        </p>

        <h1 className="mt-3 text-4xl sm:text-5xl font-bold">
          Upload Your Land Image
        </h1>

        <p className="mt-4 text-slate-400 leading-7">
          Upload a clear image of the land. LandLens AI will use it as the
          starting point for conceptual analysis and planning.
        </p>
      </div>

      <div className="mt-10 space-y-6">

        {error && (
          <ErrorMessage
            message={error}
            onClose={() => setError("")}
          />
        )}

        {!file ? (
          <UploadBox onFileSelect={handleFileSelect} />
        ) : (
          <ImagePreview
            file={file}
            onRemove={handleRemove}
          />
        )}

        <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5">

          <div className="flex gap-4">

            <div className="shrink-0 w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Info size={20} />
            </div>

            <div>
              <h3 className="font-semibold">
                About measurements
              </h3>

              <p className="mt-1 text-sm leading-6 text-slate-400">
                Measurements estimated from an ordinary photograph are
                approximate. When possible, provide a known reference
                measurement so the planning model can establish a more useful
                scale.
              </p>
            </div>

          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
              <Ruler size={19} className="text-blue-400" />
            </div>

            <div>
              <h3 className="font-semibold">
                Reference measurement
              </h3>

              <p className="text-sm text-slate-500">
                Optional for this phase
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm text-slate-400">
            The reference-measurement input will be connected to the land
            analysis workflow in the next phase.
          </p>

        </div>

        <div className="flex justify-end">

          <button
            type="button"
            disabled={!file}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 px-6 py-3.5 font-semibold transition"
          >
            Continue to Analysis
            <ArrowRight size={18} />
          </button>

        </div>

      </div>
    </section>
  );
}

export default Upload;