import { Link } from "react-router-dom";
import {
  ArrowRight,
  Camera,
  Ruler,
  LayoutGrid,
  CheckCircle2,
} from "lucide-react";

function Home() {
  return (
    <div>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(37,99,235,0.18),transparent_35%)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">

          <div className="max-w-4xl">

            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-4 py-2 text-sm text-blue-300 mb-7">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              AI-Assisted Land Planning
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-tight">
              Turn Land Images Into
              <span className="block text-blue-500">
                Smart Land Plans
              </span>
            </h1>

            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-400">
              Upload a photo of your land, provide reference measurements and
              requirements, and create conceptual land layouts with plots,
              roads, parking and planning options.
            </p>

            <div className="mt-9 flex flex-col sm:flex-row gap-4">

              <Link
                to="/upload"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 px-6 py-3.5 font-semibold transition shadow-lg shadow-blue-600/20"
              >
                Analyze My Land
                <ArrowRight size={19} />
              </Link>

              <a
                href="#how-it-works"
                className="inline-flex items-center justify-center rounded-xl border border-slate-700 hover:border-slate-500 px-6 py-3.5 font-semibold text-slate-200 transition"
              >
                See How It Works
              </a>

            </div>

            <div className="mt-9 flex flex-wrap gap-x-6 gap-y-3 text-sm text-slate-500">

              <span className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-blue-400" />
                Conceptual planning
              </span>

              <span className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-blue-400" />
                Multiple layouts
              </span>

              <span className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-blue-400" />
                2D & 3D planning
              </span>

            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">

          <div className="max-w-2xl mb-12">
            <p className="text-sm font-semibold uppercase tracking-widest text-blue-400">
              Simple workflow
            </p>

            <h2 className="mt-3 text-3xl sm:text-4xl font-bold">
              From land photo to planning concept
            </h2>

            <p className="mt-4 text-slate-400">
              LandLens AI is designed around a structured planning workflow.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">

            <StepCard
              number="01"
              icon={<Camera size={25} />}
              title="Upload Land Image"
              description="Provide an image of the land and use reference measurements when available."
            />

            <StepCard
              number="02"
              icon={<Ruler size={25} />}
              title="Define Requirements"
              description="Specify plots, road widths, parking, park area and building requirements."
            />

            <StepCard
              number="03"
              icon={<LayoutGrid size={25} />}
              title="Generate Layouts"
              description="Create conceptual layouts that can later be customized and visualized."
            />

          </div>
        </div>
      </section>

    </div>
  );
}

function StepCard({ number, icon, title, description }) {
  return (
    <div className="group rounded-2xl border border-slate-800 bg-slate-900/50 p-7 hover:border-blue-500/40 transition">

      <div className="flex items-center justify-between">
        <div className="w-12 h-12 rounded-xl bg-blue-600/10 text-blue-400 flex items-center justify-center">
          {icon}
        </div>

        <span className="text-sm font-mono text-slate-600">
          {number}
        </span>
      </div>

      <h3 className="mt-7 text-xl font-semibold">
        {title}
      </h3>

      <p className="mt-3 text-sm leading-6 text-slate-400">
        {description}
      </p>
    </div>
  );
}

export default Home;