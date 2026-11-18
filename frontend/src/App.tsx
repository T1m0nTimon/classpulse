import { createContext, useContext, useEffect, useState } from "react";
import { Route, Routes } from "react-router";
import { api, type AppConfig, type Teacher } from "./api";
import { useT } from "./i18n";
import Home from "./pages/Home";
import Join from "./pages/Join";
import SessionPage from "./pages/SessionPage";
import Student from "./pages/Student";

interface AppState { teacher: Teacher | null; setTeacher: (t: Teacher | null) => void; config: AppConfig | null }
const Ctx = createContext<AppState>({ teacher: null, setTeacher: () => {}, config: null });
export const useApp = () => useContext(Ctx);

export default function App() {
  const [teacher, setTeacher] = useState<Teacher | null | undefined>(undefined);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const { setLang, lang } = useT();

  useEffect(() => {
    api<AppConfig>("/api/config").then(setConfig).catch(() => {});
    if (location.pathname.startsWith("/j")) return setTeacher(null); // students: no auth call
    api<Teacher>("/api/auth/me").then(setTeacher).catch(() => setTeacher(null));
  }, []);

  useEffect(() => {
    if (teacher && teacher.language !== lang) setLang(teacher.language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teacher?.id]);

  if (teacher === undefined) return <div className="min-h-dvh" />;
  return (
    <Ctx.Provider value={{ teacher, setTeacher, config }}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/s/:id" element={<SessionPage />} />
        <Route path="/j" element={<Join />} />
        <Route path="/j/:code" element={<Student />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </Ctx.Provider>
  );
}
