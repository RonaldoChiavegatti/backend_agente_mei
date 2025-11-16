import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import InputField from '../components/InputField';
import Button from '../components/Button';
import { useAuth } from '../context/AuthContext';

interface RegisterForm {
  fullName: string;
  email: string;
  password: string;
}

const RegisterPage = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError
  } = useForm<RegisterForm>({
    defaultValues: { fullName: '', email: '', password: '' }
  });
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser(data.fullName, data.email, data.password);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      setError('email', { message: 'Não foi possível criar a conta.' });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 px-4">
      <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-semibold text-slate-800">Crie sua conta</h1>
          <p className="text-sm text-slate-500">Leva menos de 1 minuto.</p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <InputField
            label="Nome completo"
            placeholder="Maria Silva"
            {...register('fullName', { required: 'Informe seu nome.' })}
            error={errors.fullName?.message}
          />
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
            {...register('password', { required: 'Crie uma senha.' })}
            error={errors.password?.message}
          />
          <Button type="submit" className="w-full">
            Criar conta
          </Button>
        </form>
        <p className="text-center text-sm text-slate-500">
          Já é cadastrado?{' '}
          <Link to="/login" className="text-primary-600 font-semibold">
            Fazer login
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
