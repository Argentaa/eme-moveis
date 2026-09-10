import React from 'react';
import { motion } from 'motion/react';
import { Target, Eye, Heart } from 'lucide-react';

/**
 * About section for eMe Móveis.
 * Covers history, mission, vision, and values.
 */
export default function About() {
  const principles = [
    {
      title: 'Missão',
      desc: 'Proporcionar o bem-estar através de ambientes únicos e funcionais, superando as expectativas de nossos clientes.',
      icon: <Target className="text-red-800" size={32} />
    },
    {
      title: 'Visão',
      desc: 'Ser referência nacional em inovação e design de móveis planejados, reconhecida pela excelência técnica.',
      icon: <Eye className="text-red-800" size={32} />
    },
    {
      title: 'Valores',
      desc: 'Ética, transparência, compromisso com a qualidade e paixão pela marcenaria artesanal com toque tecnológico.',
      icon: <Heart className="text-red-800" size={32} />
    }
  ];

  return (
    <section id="sobre" className="py-24 bg-white overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Text Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <span className="text-red-800 font-bold uppercase tracking-widest text-sm">Nossa História</span>
            <h2 className="text-4xl md:text-5xl font-bold mt-4 mb-8 tracking-tight text-gray-900">
              Mais de 4 anos transformando <br />
              <span className="text-gray-400">espaços em lares.</span>
            </h2>
            <div className="space-y-6 text-gray-600 leading-relaxed text-lg">
              <p>
                A <strong>eMe Móveis</strong> nasceu do desejo de unir a tradição da marcenaria sob medida com as tendências mais modernas de design de interiores. Começamos como uma pequena oficina familiar e hoje somos uma empresa equipada com o que há de melhor em tecnologia.
              </p>
              <p>
                Nossa trajetória é marcada pela dedicação a cada projeto. Acreditamos que o móvel planejado não é apenas uma peça de decoração, mas uma extensão da personalidade de quem habita o espaço. Por isso, cada corte, acabamento e acessório é escolhido para garantir durabilidade e sofisticação.
              </p>
              <p>
                Ao escolher a eMe Móveis, você não apenas adquire mobiliário, mas investe em qualidade de vida e na valorização do seu patrimônio com uma empresa que respira excelência.
              </p>
            </div>
          </motion.div>

          {/* Image & Principles */}
          <div className="relative">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="relative z-10"
            >
              <img
                src="/images/sobre-nos.png"
                alt="Detalhe de marcenaria eMe"
                className="rounded-3xl shadow-2xl w-full h-[500px] object-cover"
                referrerPolicy="no-referrer"
              />
              {/* Floating Stat */}
              <div className="absolute -bottom-6 -left-6 bg-red-800 text-white p-8 rounded-2xl shadow-xl hidden md:block">
                <span className="text-4xl font-bold">100+</span>
                <p className="text-sm uppercase tracking-wide opacity-80 mt-1">Projetos Entregues</p>
              </div>
            </motion.div>
            
            {/* Background Accent */}
            <div className="absolute top-20 -right-10 w-64 h-64 bg-red-50 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-pulse"></div>
          </div>
        </div>

        {/* Strategic Principles Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24">
          {principles.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="bg-gray-50 p-8 rounded-2xl border border-gray-100 hover:shadow-lg transition-shadow group"
            >
              <div className="mb-6 transform transition-transform group-hover:scale-110">
                {item.icon}
              </div>
              <h3 className="text-xl font-bold mb-4">{item.title}</h3>
              <p className="text-gray-600 leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
