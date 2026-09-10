import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Calendar, Award, CheckCircle2 } from 'lucide-react';

interface TimelineItem {
  id: number;
  year: string;
  title: string;
  description: string;
  image?: string;
}

export default function Timeline() {
  const [timelineItems, setTimelineItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fallbackTimeline: TimelineItem[] = [
    {
      id: 1,
      year: '2022',
      title: 'Fundação da eMe Móveis',
      description: 'Nascimento da eMe Móveis no Rio Grande do Sul, com foco inicial em cozinhas planejadas e painéis.',
      image: 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&q=80&w=600'
    },
    {
      id: 2,
      year: '2023',
      title: 'Primeiro móvel produzido',
      description: 'Entrega do primeiro dormitório completo com ferragens telescópicas e iluminação integrada de alto padrão.',
      image: 'https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&q=80&w=600'
    },
    {
      id: 3,
      year: '2024',
      title: 'Sede e show-room próprio',
      description: 'Inauguração de nossa sede em Frederico Westphalen/RS, apresentando as últimas tendências em acabamentos e MDF premium.',
      image: 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=600'
    },
    {
      id: 4,
      year: '2026',
      title: 'Mais de 100 Projetos Entregues',
      description: 'Marca histórica de projetos entregues e clientes satisfeitos em nossa região, unindo qualidade e exclusividade.',
      image: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&q=80&w=600'
    }
  ];

  useEffect(() => {
    fetch('/api/timeline')
      .then((res) => {
        if (!res.ok) throw new Error('Falha ao buscar linha do tempo');
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setTimelineItems(data);
        } else {
          setTimelineItems(fallbackTimeline);
        }
      })
      .catch((err) => {
        console.warn('Erro ao carregar endpoint, usando fallback:', err);
        setTimelineItems(fallbackTimeline);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <section id="linha-tempo" className="py-14 bg-black text-white relative overflow-hidden border-t border-gray-900">
      {/* Aesthetic Background Lighting */}
      <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-red-950/20 rounded-full mix-blend-multiply filter blur-3xl opacity-50 pointer-events-none"></div>
      <div className="absolute bottom-1/4 -right-1/4 w-96 h-96 bg-red-950/20 rounded-full mix-blend-multiply filter blur-3xl opacity-50 pointer-events-none"></div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header Section */}
        <div className="text-center mb-10">
          <motion.span 
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-red-800 font-bold uppercase tracking-widest text-xs"
          >
            Nossa Evolução
          </motion.span>
          <motion.h2 
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-3xl md:text-4xl font-bold mt-2 mb-4 tracking-tight text-white"
          >
            Linha do Tempo <span className="text-gray-500 font-light">e Conquistas</span>
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="max-w-2xl mx-auto text-gray-400 text-base"
          >
            Acompanhe nossa trajetória de superação, investimento tecnológico e excelência na satisfação de lares e empresas.
          </motion.p>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-red-800"></div>
          </div>
        ) : (
          /* Vertical Timeline Container */
          <div className="relative mt-8">
            {/* Center Vertical Line (Desktop only) */}
            <div className="absolute left-1/2 transform -translate-x-1/2 h-full w-[2px] bg-red-950/60 hidden md:block z-0"></div>

            {/* Left Vertical Line (Mobile only) */}
            <div className="absolute left-6 h-full w-[2px] bg-red-950/60 md:hidden z-0"></div>

            <div className="space-y-6 relative z-10">
              {timelineItems.map((item, index) => {
                const isEven = index % 2 === 0;

                return (
                  <motion.div
                    key={item.id || index}
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-50px' }}
                    transition={{ duration: 0.5 }}
                    className="flex flex-col md:flex-row items-stretch w-full animate-fade-in"
                  >
                    {/* Time Frame node - Alternate sides (desktop) */}
                    <div className="md:w-1/2 flex items-center md:justify-end md:pr-10 pl-12 md:pl-0 relative mb-2 md:mb-0">
                      
                      {/* Interactive Year Badge */}
                      <div className={`flex flex-col ${isEven ? 'md:items-end' : 'md:items-start'} md:w-full`}>
                        <div className="bg-red-950/40 border border-red-800/50 text-red-500 font-extrabold text-xl md:text-2xl px-4 py-1.5 rounded-full inline-block font-mono shadow-md">
                          {item.year}
                        </div>
                      </div>

                      {/* Timeline Central Dot (Desktop) */}
                      <div className="absolute right-0 top-1/2 transform translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-black border-4 border-red-800 rounded-full hidden md:block z-20 shadow-lg group-hover:scale-125 transition-transform"></div>

                      {/* Timeline Dot (Mobile) */}
                      <div className="absolute left-6 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-black border-4 border-red-800 rounded-full md:hidden z-20"></div>
                    </div>

                    {/* Content Block (Card) */}
                    <div className={`md:w-1/2 pl-12 md:pl-10 flex ${isEven ? 'md:justify-start' : 'md:justify-start md:-order-1 md:pr-10 md:pl-0'}`}>
                      <div className="w-full bg-[#0d0d0d] border border-gray-900 rounded-2xl p-4 sm:p-5 hover:border-red-800/40 transition-all duration-300 shadow-xl max-w-xl group flex flex-col sm:flex-row gap-4 items-center">
                        {/* Render item image if it exists */}
                        {item.image && (
                          <div className="w-full sm:w-28 h-32 sm:h-20 rounded-xl overflow-hidden shrink-0">
                            <img 
                              src={item.image} 
                              alt={item.title} 
                              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                              referrerPolicy="no-referrer"
                            />
                          </div>
                        )}
                        
                        <div className="flex-1 min-w-0 text-left">
                          <h3 className="text-base font-bold mb-1 tracking-tight group-hover:text-red-500 transition-colors">
                            {item.title}
                          </h3>
                          <p className="text-gray-400 leading-relaxed text-xs">
                            {item.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
