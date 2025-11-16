import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FiLogOut, FiMessageSquare, FiFileText, FiHome, FiCreditCard } from 'react-icons/fi';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: FiHome },
  { to: '/documents', label: 'Documentos', icon: FiFileText },
  { to: '/agent', label: 'Agente IA', icon: FiMessageSquare },
  { to: '/billing', label: 'Faturamento', icon: FiCreditCard }
];

const MainLayout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white shadow-sm border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <span className="font-semibold text-lg text-primary-700">Agente MEI</span>
            <nav className="hidden sm:flex items-center gap-4 text-sm font-medium text-slate-500">
              {navItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `px-2 py-1 rounded-md transition-colors ${
                      isActive ? 'text-primary-600 bg-primary-50' : 'hover:text-primary-600'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-700">{user?.full_name ?? user?.email}</p>
              <p className="text-xs text-slate-400">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              <FiLogOut />
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="sm:hidden bg-white border-b border-slate-100 px-4 py-3 flex gap-2 overflow-x-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex-1 min-w-[120px] flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                isActive ? 'bg-primary-50 border-primary-200 text-primary-600' : 'border-slate-200 text-slate-500'
              }`
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </div>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
