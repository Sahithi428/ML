import { createContext, useContext, useMemo, useState } from "react";

const ProjectContext = createContext(null);

export function ProjectProvider({ children }) {
  const [project, setProject] = useState({
    name: "",
    image: null,
    imagePreview: null,
    measurement: null,
    requirements: {},
  });

  const updateProject = (updates) => {
    setProject((current) => ({
      ...current,
      ...updates,
    }));
  };

  const clearProject = () => {
    setProject({
      name: "",
      image: null,
      imagePreview: null,
      measurement: null,
      requirements: {},
    });
  };

  const value = useMemo(
    () => ({
      project,
      updateProject,
      clearProject,
    }),
    [project]
  );

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);

  if (!context) {
    throw new Error(
      "useProject must be used inside ProjectProvider."
    );
  }

  return context;
}