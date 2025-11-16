import { useForm } from 'react-hook-form';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import InputField from '../components/InputField';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

interface LoginForm {
  email: string;
  password: string;
}

const LoginPage = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError
  } = useForm<LoginForm>({
    defaultValues: { email: '', password: '' }
  });
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | undefined)?.from?.pathname ?? '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (data: LoginForm) => {
    try {
      await login(data.email, data.password);
      navigate(from, { replace: true });
    } catch (error) {
      setError('password', { message: 'E-mail ou senha inválidos.' });
    }
  };

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 px-4">
      <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-semibold text-slate-800">Bem-vindo ao Agente MEI</h1>
          <p className="text-sm text-slate-500">Entre com seu e-mail e senha para continuar.</p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <InputField
            label="E-mail"
            type="email"
            placeholder="seu@email.com"
            {...register('email', { required: 'Informe seu e-mail.' })}
            error={errors.email?.message}
          />
          <InputField
            label="Senha"
            type="password"
            placeholder="********"
            {...register('password', { required: 'Informe sua senha.' })}
            error={errors.password?.message}
          />
          <Button type="submit" className="w-full">
            Entrar
          </Button>
        </form>
        <p className="text-center text-sm text-slate-500">
          Ainda não tem conta?{' '}
          <Link to="/register" className="text-primary-600 font-semibold">
            Cadastre-se
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
