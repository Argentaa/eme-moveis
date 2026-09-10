import React from 'react';
import { Instagram, Mail, Phone, MapPin } from 'lucide-react';

/**
 * Footer component for EME Móveis.
 * Displays contact info, social links, and simple copyright.
 */
export default function Footer() {
  return (
    <footer className="bg-black text-white pt-16 pb-8 border-t border-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
          {/* Brand Column */}
          <div>
            <img
              src="/images/logo/logo-eme-moveis.png"
              alt="eMe Móveis"
              className="h-16 w-auto mb-4 select-none"
              draggable={false}
            />
            <p className="text-gray-400 leading-relaxed max-w-sm">
              Transformando seus sonhos em realidade com móveis planejados de alta qualidade e design exclusivo para cada ambiente.
            </p>
          </div>

          {/* Links Column */}
          <div>
            <h4 className="text-lg font-semibold mb-6">Navegação</h4>
            <ul className="space-y-4">
              <li><a href="#home" className="text-gray-400 hover:text-red-800 transition-colors">Início</a></li>
              <li><a href="#sobre" className="text-gray-400 hover:text-red-800 transition-colors">Sobre Nós</a></li>
              <li><a href="#portfolio" className="text-gray-400 hover:text-red-800 transition-colors">Portfólio</a></li>
              <li><a href="#contato" className="text-gray-400 hover:text-red-800 transition-colors">Contato</a></li>
            </ul>
          </div>

          {/* Contact Column */}
          <div>
            <h4 className="text-lg font-semibold mb-6">Contato</h4>
            <ul className="space-y-4 text-gray-400">
              <li className="flex items-center gap-3">
                <Phone size={18} className="text-red-800" />
                <span>(55) 99717-5619</span>
              </li>
              <li className="flex items-center gap-3">
                <Instagram size={18} className="text-red-800" />
                <a 
                  href="https://www.instagram.com/ememoveis" 
                  target="_blank" 
                  rel="noreferrer" 
                  className="hover:text-red-800 transition-colors"
                >
                  @ememoveis
                </a>
              </li>
              <li className="flex items-center gap-3">
                <Mail size={18} className="text-red-800" />
                <span>atendimento@ememoveis.com.br</span>
              </li>
              <li className="flex items-center gap-3">
                <MapPin size={18} className="text-red-800" />
                <span>Frederico Westphalen, RS</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-gray-900 flex flex-col sm:flex-row justify-between items-center gap-4 text-gray-500 text-sm">
          <p>© {new Date().getFullYear()} EME Móveis Planejados. Todos os direitos reservados.</p>
          <a 
            href="/admin" 
            className="text-xs text-gray-600 hover:text-red-700 transition-colors hover:underline"
          >
            Área Restrita (Painel Administrativo)
          </a>
        </div>
      </div>
    </footer>
  );
}
