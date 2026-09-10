import React from 'react';
import { motion } from 'motion/react';

/**
 * Hero section for the landing page.
 * Features a high-impact banner with a call to action.
 */
export default function Hero() {
  return (
    <section id="home" className="relative h-screen w-full flex items-center justify-center overflow-hidden">
      {/* Background Image with Overlay */}
      <div className="absolute inset-0 z-0">
        <img
          src="/images/banner-principal.png"
          alt="Ambiente planejado luxuoso"
          className="w-full h-full object-cover"
          referrerPolicy="no-referrer"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-transparent"></div>
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-white">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-2xl"
        >
          <h1 className="text-5xl md:text-7xl font-bold leading-tight mb-6 tracking-tighter">
            Elegância em cada <span className="text-red-800 italic">detalhe.</span>
          </h1>
          <p className="text-xl md:text-2xl text-gray-300 mb-10 font-light">
            Móveis planejados que unem sofisticação, funcionalidade e o estilo que sua casa merece.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <a
              href="#contato"
              className="bg-red-800 hover:bg-red-900 text-white px-8 py-4 rounded-full text-lg font-bold text-center transition-all shadow-xl hover:shadow-red-900/40"
            >
              Solicitar Orçamento
            </a>
            <a
              href="#portfolio"
              className="bg-transparent border-2 border-white/30 hover:border-white text-white px-8 py-4 rounded-full text-lg font-bold text-center transition-all backdrop-blur-sm"
            >
              Ver Projetos
            </a>
          </div>
        </motion.div>
      </div>

      {/* Scroll Indicator */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10 animate-bounce">
        <div className="w-1 h-12 rounded-full bg-gradient-to-b from-red-800 to-transparent"></div>
      </div>
    </section>
  );
}
