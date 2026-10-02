const state = {
  filename:null, imageUrl:null, measurement:null, requirements:null, layouts:[],
  selectedLayout:null, selectedPlot:null, building:null, currentFloor:0, zoom:1
};

const $ = id => document.getElementById(id);
function toast(msg){const el=document.createElement("div");el.className="toast";el.textContent=msg;$("toast").appendChild(el);setTimeout(()=>el.remove(),2800)}
function showPage(id){
  document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
  $(id).classList.add("active");
  window.scrollTo({top:0,behavior:"smooth"});
  if(id==="projects"||id==="dashboard") loadProjects();
}
function toggleTheme(){document.body.classList.toggle("dark");localStorage.setItem("landlens-dark",document.body.classList.contains("dark"))}
if(localStorage.getItem("landlens-dark")==="true")document.body.classList.add("dark");

const drop=$("dropzone");
drop.addEventListener("dragover",e=>{e.preventDefault();drop.classList.add("drag")});
drop.addEventListener("dragleave",()=>drop.classList.remove("drag"));
drop.addEventListener("drop",e=>{e.preventDefault();drop.classList.remove("drag");handleFile(e.dataTransfer.files[0])});

function resetUpload(){state.filename=null;state.imageUrl=null;$("file").value="";$("preview-wrap").classList.add("hidden");$("dropzone").classList.remove("hidden");$("analyze-btn").disabled=true}
function handleFile(file){
  if(!file)return;
  if(!file.type.startsWith("image/"))return toast("Please select an image.");
  const reader=new FileReader();reader.onload=()=>{$("preview").src=reader.result;$("preview-wrap").classList.remove("hidden");$("dropzone").classList.add("hidden");$("file-name").textContent=file.name;$("analyze-btn").disabled=false};reader.readAsDataURL(file);
  const fd=new FormData();fd.append("image",file);
  fetch("/api/upload",{method:"POST",body:fd}).then(r=>r.json()).then(d=>{if(d.error)throw Error(d.error);state.filename=d.filename;state.imageUrl=d.url;toast("Image uploaded successfully.")}).catch(e=>toast(e.message));
}
async function analyze(){
  if(!state.filename)return toast("Upload an image first.");
  $("analyze-btn").disabled=true;$("analyze-btn").textContent="Analyzing…";
  try{
    const r=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filename:state.filename,reference_ft:parseFloat($("reference").value)||0})});
    const d=await r.json();if(d.error)throw Error(d.error);state.measurement=d;
    $("analysis-image").src=state.imageUrl;$("m-area").textContent=d.area_sqft.toLocaleString();$("m-length").textContent=d.length_ft;$("m-width").textContent=d.width_ft;$("m-confidence").textContent=Math.round(d.confidence*100)+"%";$("m-type").textContent=d.measurement_type.replaceAll("_"," ");
    $("analysis-notes").innerHTML=d.notes.map(x=>`<div class="note">✓ ${x}</div>`).join("");
    showPage("analysis");
  }catch(e){toast(e.message)}finally{$("analyze-btn").disabled=false;$("analyze-btn").textContent="Analyze Land →"}
}
function requirements(){
  return {
    plot_count:parseInt($("plot-count").value)||8,
    max_floors:parseInt($("max-floors").value)||2,
    main_road_width:parseFloat($("main-road").value)||30,
    internal_road_width:parseFloat($("internal-road").value)||20,
    park_percent:parseFloat($("park-percent").value)||8,
    parking_percent:parseFloat($("parking-percent").value)||10
  }
}
async function generateLayouts(){
  if(!state.measurement)return toast("Complete analysis first.");
  state.requirements=requirements();
  const r=await fetch("/api/layouts/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({measurement:state.measurement,requirements:state.requirements})});
  const d=await r.json();if(d.error)return toast(d.error);state.layouts=d.layouts;renderLayoutCards();showPage("layouts");
}
function miniSVG(layout){
  const L=layout.land.length_ft,W=layout.land.width_ft;
  let s=`<svg class="mini-plan" viewBox="0 0 ${L} ${W}" preserveAspectRatio="none"><rect width="${L}" height="${W}" fill="#f3f6f8" stroke="#9fb0bf"/>`;
  layout.roads.forEach(r=>s+=`<rect x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}" fill="#cbd5df"/>`);
  s+=`<rect x="${layout.parking.x}" y="${layout.parking.y}" width="${layout.parking.width}" height="${layout.parking.height}" fill="#ffe4ad" stroke="#d49a2c"/><rect x="${layout.park.x}" y="${layout.park.y}" width="${layout.park.width}" height="${layout.park.height}" fill="#ccefd6" stroke="#3d9d5b"/>`;
  layout.plots.forEach(p=>s+=`<rect x="${p.x}" y="${p.y}" width="${p.width}" height="${p.height}" fill="#dbeaff" stroke="#4b83d1" stroke-width=".6"/>`);
  return s+"</svg>";
}
function renderLayoutCards(){
  $("layout-cards").innerHTML=state.layouts.map((l,i)=>`
  <div class="layout-option">
    ${miniSVG(l)}
    <div class="eyebrow">OPTION ${i+1}</div><h3>${l.name}</h3>
    <div class="stats-grid">
      <div class="stat"><small>Plots</small><b>${l.stats.plot_count}</b></div>
      <div class="stat"><small>Total area</small><b>${l.land.area_sqft.toLocaleString()} sq ft</b></div>
      <div class="stat"><small>Main road</small><b>${l.stats.main_road_width} ft</b></div>
      <div class="stat"><small>Internal road</small><b>${l.stats.internal_road_width} ft</b></div>
      <div class="stat"><small>Common park</small><b>${l.stats.park_area.toLocaleString()} sq ft</b></div>
      <div class="stat"><small>Common parking</small><b>${l.stats.parking_area.toLocaleString()} sq ft</b></div>
    </div>
    <button class="primary" onclick="openLayout(${i})">Open Planner →</button>
  </div>`).join("");
}
function openLayout(i){state.selectedLayout=state.layouts[i];renderPlan();showPage("planner")}
function renderPlan(){
  const l=state.selectedLayout;if(!l)return;
  const L=l.land.length_ft,W=l.land.width_ft;
  let svg=`<svg viewBox="-5 -5 ${L+10} ${W+10}" xmlns="http://www.w3.org/2000/svg" style="width:${Math.min(900,L*5)*state.zoom}px"><rect x="0" y="0" width="${L}" height="${W}" rx="1" fill="#f4f7f9" stroke="#7f95a8" stroke-width="1.5"/>`;
  l.roads.forEach(r=>{svg+=`<rect x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}" fill="#cbd5df"/><text x="${r.width/2}" y="${r.y+r.height/2+1}" text-anchor="middle" font-size="${Math.max(2.5,L/90)}" fill="#465a6c" font-weight="700">${r.name} · ${r.width_ft} FT</text>`});
  svg+=`<rect x="${l.parking.x}" y="${l.parking.y}" width="${l.parking.width}" height="${l.parking.height}" fill="#ffe4ad" stroke="#d39c36"/><text x="${l.parking.x+l.parking.width/2}" y="${l.parking.y+l.parking.height/2}" text-anchor="middle" font-size="${Math.max(2.5,L/95)}" fill="#7d5a16" font-weight="700">COMMON PARKING</text>`;
  svg+=`<rect x="${l.park.x}" y="${l.park.y}" width="${l.park.width}" height="${l.park.height}" fill="#ccefd6" stroke="#3d9d5b"/><text x="${l.park.x+l.park.width/2}" y="${l.park.y+l.park.height/2}" text-anchor="middle" font-size="${Math.max(2.5,L/95)}" fill="#267141" font-weight="700">COMMON PARK</text>`;
  l.plots.forEach(p=>{svg+=`<g onclick="selectPlot(${p.id})" style="cursor:pointer"><rect x="${p.x}" y="${p.y}" width="${p.width}" height="${p.height}" fill="${state.selectedPlot&&state.selectedPlot.id===p.id?'#b9d6ff':'#dceaff'}" stroke="#3f78c9" stroke-width="1"/><text x="${p.x+p.width/2}" y="${p.y+p.height/2-1}" text-anchor="middle" font-size="${Math.max(2.8,L/90)}" fill="#234b77" font-weight="800">PLOT ${String(p.id).padStart(2,"0")}</text><text x="${p.x+p.width/2}" y="${p.y+p.height/2+4}" text-anchor="middle" font-size="${Math.max(2,L/120)}" fill="#36566f">${p.dimensions}</text></g>`});
  svg+=`<circle cx="${l.entry.x}" cy="0" r="${Math.max(2,L/120)}" fill="#16a34a"/><text x="${l.entry.x}" y="${Math.max(4,L/100)}" text-anchor="middle" font-size="${Math.max(2.5,L/110)}" fill="#166534" font-weight="800">ENTRY / EXIT</text></svg>`;
  $("svg-container").innerHTML=svg;
}
function selectPlot(id){
  const p=state.selectedLayout.plots.find(x=>x.id===id);state.selectedPlot=p;
  $("selection").innerHTML=`<div class="detail-list">
    <div class="detail-row"><span>Plot number</span><b>Plot ${String(p.id).padStart(2,"0")}</b></div>
    <div class="detail-row"><span>Dimensions</span><b>${p.dimensions}</b></div>
    <div class="detail-row"><span>Area</span><b>${p.area_sqft.toLocaleString()} sq ft</b></div>
    <div class="detail-row"><span>Floors</span><b>Up to ${p.floors}</b></div>
    <button class="primary" onclick="openBuilding()">Open Building Planner →</button>
  </div>`;
  renderPlan();
}
function zoom(dir){state.zoom=clamp(state.zoom+dir*.15,.7,1.7);renderPlan()}
function fitPlan(){state.zoom=1;renderPlan()}
function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
async function openBuilding(){
  if(!state.selectedPlot)return toast("Select a plot first.");
  const r=await fetch("/api/buildings/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({plot:state.selectedPlot,floors:state.requirements.max_floors})});
  state.building=await r.json();state.currentFloor=0;renderBuilding();showPage("building");
}
function renderBuilding(){
  const b=state.building.building;const f=b.floors[state.currentFloor];
  let svg=`<svg class="floor-svg" viewBox="0 0 ${b.width_ft} ${b.depth_ft}" xmlns="http://www.w3.org/2000/svg"><rect width="${b.width_ft}" height="${b.depth_ft}" fill="#f8fafc" stroke="#60788d"/>`;
  f.rooms.forEach(r=>{svg+=`<rect x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}" fill="#e8f1fb" stroke="#527da8"/><text x="${r.x+r.width/2}" y="${r.y+r.height/2}" text-anchor="middle" font-size="3" fill="#274b6d" font-weight="700">${r.name}</text>`});
  svg+=`</svg>`;
  $("building-content").innerHTML=`<div class="building-card"><div class="card"><h3>Building summary</h3><div class="detail-list"><div class="detail-row"><span>Plot</span><b>${state.selectedPlot.id}</b></div><div class="detail-row"><span>Footprint</span><b>${b.footprint_sqft} sq ft</b></div><div class="detail-row"><span>Building size</span><b>${b.width_ft} × ${b.depth_ft} ft</b></div><div class="detail-row"><span>Floors</span><b>${b.floors.length}</b></div></div></div><div class="card"><div class="floor-tabs">${b.floors.map((x,i)=>`<button class="floor-tab ${i===state.currentFloor?'active':''}" onclick="state.currentFloor=${i};renderBuilding()">${x.label}</button>`).join("")}</div><h3>${f.label}</h3>${svg}<div class="note">Conceptual room arrangement only. Verify local setbacks, ventilation, structure, stairs, fire safety and building codes.</div></div></div>`;
}
function show3D(){
  $("three-scene").innerHTML=`<div class="three-scene"><div class="isometric"><div class="ground"></div><div class="road3"></div><div class="three-label">MAIN ROAD · COMMON ENTRY</div><div class="building b1"></div><div class="building b2"></div><div class="building b3"></div><div class="building b4"></div><div class="tree t1"></div><div class="tree t2"></div><div class="tree t3"></div><div class="parking3"></div></div></div>`;
  showPage("view3d");
}
async function saveCurrentProject(){
  if(!state.layouts.length)return toast("Generate a layout first.");
  const name=prompt("Project name:", "LandLens Project")||"LandLens Project";
  const r=await fetch("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,image:state.filename,measurement:state.measurement,requirements:state.requirements,layouts:state.layouts})});
  const d=await r.json();if(d.error)return toast(d.error);toast("Project saved.");
  const rr=await fetch("/api/reports/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({project:d})});
  const report=await rr.json();if(report.url)toast("PDF report ready.");
  setTimeout(()=>{if(report.url && confirm("Project saved. Download PDF report now?"))window.location=report.url},400);
}
async function loadProjects(){
  const r=await fetch("/api/projects");const items=await r.json();
  $("dash-projects").textContent=items.length;$("dash-layouts").textContent=items.reduce((n,p)=>n+(p.layouts?.length||0),0);
  const html=items.length?items.map(p=>`<div class="project-row"><div><h4>${p.name}</h4><small>${new Date(p.created_at).toLocaleString()} · ${p.measurement?.area_sqft?.toLocaleString()||"—"} sq ft</small></div><div class="project-actions"><button class="secondary small" onclick='openSaved(${JSON.stringify(p).replaceAll("'","&#39;")})'>Open</button><button class="secondary small" onclick="deleteProject('${p.id}')">Delete</button></div></div>`).join(""):`<div class="empty">No saved projects yet. Create your first land plan.</div>`;
  $("projects-list").innerHTML=html;$("recent-projects").innerHTML=html;
}
function openSaved(p){state.filename=p.image;state.measurement=p.measurement;state.requirements=p.requirements;state.layouts=p.layouts;state.selectedLayout=p.layouts[0];renderLayoutCards();showPage("layouts")}
async function deleteProject(id){if(!confirm("Delete this project?"))return;await fetch("/api/projects/"+id,{method:"DELETE"});toast("Project deleted.");loadProjects()}
loadProjects();
