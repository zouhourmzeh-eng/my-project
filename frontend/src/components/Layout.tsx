import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { NotificationBell } from "./NotificationBell";

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <header className="bg-brand-600 text-white shadow-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="text-xl font-bold tracking-tight hover:opacity-90 transition-opacity flex items-center gap-2">
            <span className="bg-white text-brand-600 px-2 py-0.5 rounded font-black text-sm">QMS</span>
            <span className="hidden sm:inline font-semibold">Quality Management</span>
          </Link>

          <nav className="flex items-center gap-1 sm:gap-2 text-sm font-medium">
            <NavLink
              to="/dashboard"
              end
              className={({ isActive }) =>
                isActive
                  ? "bg-brand-700 px-3 py-2 rounded-lg"
                  : "hover:bg-brand-500 px-3 py-2 rounded-lg transition-colors"
              }
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/projects"
              className={({ isActive }) =>
                isActive
                  ? "bg-brand-700 px-3 py-2 rounded-lg"
                  : "hover:bg-brand-500 px-3 py-2 rounded-lg transition-colors"
              }
            >
              Projects
            </NavLink>

            {user?.role === "consultant" && (
              <>
                <NavLink
                  to="/archived"
                  className={({ isActive }) =>
                    isActive
                      ? "bg-brand-700 px-3 py-2 rounded-lg hidden md:block"
                      : "hover:bg-brand-500 px-3 py-2 rounded-lg transition-colors hidden md:block"
                  }
                >
                  Archived
                </NavLink>
                <NavLink
                  to="/regulatory-watch"
                  className={({ isActive }) =>
                    isActive
                      ? "bg-brand-700 px-3 py-2 rounded-lg hidden md:block"
                      : "hover:bg-brand-500 px-3 py-2 rounded-lg transition-colors hidden md:block"
                  }
                >
                  Regulatory
                </NavLink>
              </>
            )}

            <NavLink
              to="/settings"
              className={({ isActive }) =>
                isActive
                  ? "bg-brand-700 px-3 py-2 rounded-lg"
                  : "hover:bg-brand-500 px-3 py-2 rounded-lg transition-colors"
              }
            >
              Settings
            </NavLink>

            <div className="flex items-center gap-3 ml-3 pl-3 border-l border-brand-500">
              <NotificationBell />
              {user && (
                <div className="hidden lg:flex flex-col items-end leading-none gap-0.5">
                  <span className="text-sm font-bold">{user.full_name}</span>
                  <span className="text-[10px] uppercase tracking-widest text-brand-200">{user.role}</span>
                </div>
              )}
              <button
                onClick={() => { logout(); nav("/"); }}
                className="bg-white text-brand-600 hover:bg-brand-50 px-3 py-2 rounded-lg font-bold text-xs transition-all shadow-sm"
              >
                Sign out
              </button>
            </div>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>

      <footer className="py-5 text-center text-slate-400 text-xs border-t bg-white mt-auto">
        &copy; {new Date().getFullYear()} QMS Platform · Quality &amp; Regulatory Compliance
      </footer>
    </div>
  );
}
