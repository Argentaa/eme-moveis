import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Phone, Instagram, Mail, Send, CheckCircle2 } from 'lucide-react';

/**
 * Contact section for eMe Móveis.
 * Includes contact info cards and a simple status-handled form.
 */
export default function Contact() {
  const [formStatus, setFormStatus] = useState<'idle' | 'sending' | 'success'>('idle');

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormStatus('sending');

    const formData = new FormData(e.currentTarget);
    const name = formData.get('name') as string;
    const phone = formData.get('phone') as string;
    const email = formData.get('email') as string;
    const message = formData.get('message') as string;

    // Número da eMe Móveis (substitua pelo seu número real)
    const whatsappNumber = "55997175616";
    
    // Formata a mensagem para o WhatsApp
    const text = `Olá! Meu nome é ${name}.
Gostaria de um orçamento para móveis planejados.
📞 Telefone: ${phone}
📧 Email: ${email}
💬 Mensagem: ${message}`;

    const encodedText = encodeURIComponent(text);
    const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodedText}`;

    // Simula um pequeno atraso para dar feedback visual antes de redirecionar
    setTimeout(() => {
      setFormStatus('success');
      
      // Abre o WhatsApp em uma nova aba
      window.open(whatsappUrl, '_blank');

      setTimeout(() => setFormStatus('idle'), 3000);
    }, 1000);
  };

  return (
    <section id="contato" className="py-24 bg-white relative overflow-hidden">
      {/* Decorative background element */}
      <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 bg-red-50 rounded-full filter blur-3xl opacity-50"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-16">
          <span className="text-red-800 font-bold uppercase tracking-widest text-sm">Contato</span>
          <h2 className="text-4xl md:text-5xl font-bold mt-4 mb-6 tracking-tight">
            Vamos planejar seu <span className="text-red-800 italic">próximo projeto?</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          {/* Contact Information */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h3 className="text-2xl font-bold mb-8 text-gray-900 leading-tight">
              Fale com um de nossos <br />especialistas agora mesmo.
            </h3>
            
            <div className="space-y-6">
              {/* Social/Link Cards */}
              <a 
                href="https://wa.me/55997175616" 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center gap-5 p-6 bg-gray-50 rounded-2xl border border-transparent hover:border-red-800/30 hover:bg-white hover:shadow-lg transition-all group"
              >
                <div className="w-12 h-12 bg-red-800 rounded-full flex items-center justify-center text-white shrink-0 group-hover:scale-110 transition-transform">
                  <Phone size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-500 uppercase font-bold tracking-wider">WhatsApp</p>
                  <p className="text-lg font-bold text-gray-900 group-hover:text-red-800 transition-colors">(55) 9717-5616</p>
                </div>
              </a>

              <a 
                href="https://www.instagram.com/ememoveis" 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center gap-5 p-6 bg-gray-50 rounded-2xl border border-transparent hover:border-red-800/30 hover:bg-white hover:shadow-lg transition-all group"
              >
                <div className="w-12 h-12 bg-red-800 rounded-full flex items-center justify-center text-white shrink-0 group-hover:scale-110 transition-transform">
                  <Instagram size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-500 uppercase font-bold tracking-wider">Instagram</p>
                  <p className="text-lg font-bold text-gray-900 group-hover:text-red-800 transition-colors">@ememoveis</p>
                </div>
              </a>

              <div className="flex items-center gap-5 p-6 bg-gray-50 rounded-2xl border border-transparent hover:bg-white hover:shadow-sm transition-all group">
                <div className="w-12 h-12 bg-red-800 rounded-full flex items-center justify-center text-white shrink-0 group-hover:scale-110 transition-transform">
                  <Mail size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-500 uppercase font-bold tracking-wider">Email</p>
                  <p className="text-lg font-bold text-gray-900">atendimento@ememoveis.com.br</p>
                </div>
              </div>
            </div>
            
            <p className="mt-12 text-gray-500 italic">
              * Atendimento de Segunda a Sexta, das 08h às 18h.
            </p>
          </motion.div>

          {/* Form */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="bg-gray-50 p-8 md:p-10 rounded-3xl border border-gray-100 shadow-xl shadow-gray-200/50"
          >
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Seu Nome</label>
                <input 
                  type="text" 
                  name="name"
                  required
                  placeholder="Ex: João Silva"
                  className="w-full bg-white border border-gray-200 rounded-xl px-5 py-4 focus:outline-none focus:ring-2 focus:ring-red-800/20 focus:border-red-800 transition-all placeholder:text-gray-300" 
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">WhatsApp</label>
                  <input 
                    type="tel" 
                    name="phone"
                    required
                    placeholder="(00) 00000-0000"
                    className="w-full bg-white border border-gray-200 rounded-xl px-5 py-4 focus:outline-none focus:ring-2 focus:ring-red-800/20 focus:border-red-800 transition-all placeholder:text-gray-300" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Email</label>
                  <input 
                    type="email" 
                    name="email"
                    required
                    placeholder="voce@exemplo.com"
                    className="w-full bg-white border border-gray-200 rounded-xl px-5 py-4 focus:outline-none focus:ring-2 focus:ring-red-800/20 focus:border-red-800 transition-all placeholder:text-gray-300" 
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Mensagem</label>
                <textarea 
                  name="message"
                  rows={4}
                  required
                  placeholder="Conte-nos um pouco sobre o projeto que você tem em mente..."
                  className="w-full bg-white border border-gray-200 rounded-xl px-5 py-4 focus:outline-none focus:ring-2 focus:ring-red-800/20 focus:border-red-800 transition-all placeholder:text-gray-300 resize-none" 
                ></textarea>
              </div>

              <button
                type="submit"
                disabled={formStatus !== 'idle'}
                className={`w-full py-5 rounded-xl font-bold flex items-center justify-center gap-3 transition-all transform active:scale-95 ${
                  formStatus === 'success' 
                    ? 'bg-green-600 text-white' 
                    : formStatus === 'sending'
                    ? 'bg-red-900 text-white opacity-70 cursor-wait'
                    : 'bg-black text-white hover:bg-red-950 shadow-lg'
                }`}
              >
                {formStatus === 'success' ? (
                  <>
                    <CheckCircle2 size={24} />
                    Abrindo WhatsApp...
                  </>
                ) : formStatus === 'sending' ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Preparando Mensagem...
                  </>
                ) : (
                  <>
                    <Send size={20} />
                    Enviar Orçamento via WhatsApp
                  </>
                )}
              </button>
            </form>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
