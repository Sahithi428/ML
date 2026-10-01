import { Link } from "react-router-dom";
import {
  FolderOpen,
  Map,
  Ruler,
  Plus,
  ArrowRight,
} from "lucide-react";

function Dashboard() {
  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">

      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">

        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-blue-400">
            Workspace
          </p>

          <h1 className="mt-3 text-4xl font-bold">
            Dashboard
          </h1>

          <p className="mt-3 text-slate-400">
            Manage your land-planning projects.
          </p>
        </div>

        <Link
          to="/upload"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 px-5 py-3 font-semibold transition"
        >
          <Plus size={18} />
          New Project
        </Link>

      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-10">

        <StatCard
          icon={<FolderOpen size={21} />}
          label="Projects"
          value="0"
        />

        <StatCard
          icon={<Map size={21} />}
          label="Layouts"
          value="0"
        />

        <StatCard
          icon={<Ruler size={21} />}
          label="Land Analyses"
          value="0"
        />

        <StatCard
          icon={<Map size={21} />}
          label="Generated Plans"
          value="0"
        />

      </div>

      <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-10 text-center">

        <div className="mx-auto w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center">
          <FolderOpen size={25} className="text-slate-500" />
        </div>

        <h2 className="mt-5 text-xl font-semibold">
          No projects yet
        </h2>

        <p className="mt-2 max-w-md mx-auto text-sm leading-6 text-slate-500">
          Upload a land image to create your first LandLens AI conceptual
          planning project.
        </p>

        <Link
          to="/upload"
          className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue-400 hover:text-blue-300"
        >
          Create your first project
          <ArrowRight size={16} />
        </Link>

      </div>

    </section>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">

      <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
        {icon}
      </div>

      <p className="mt-5 text-sm text-slate-500">
        {label}
      </p>

      <p className="mt-1 text-3xl font-bold">
        {value}
      </p>

    </div>
  );
}

export default Dashboard;