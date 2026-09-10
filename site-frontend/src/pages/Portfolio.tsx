import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, ChevronLeft, ChevronRight, Maximize2 } from 'lucide-react';

/**
 * Portfolio section for eMe Móveis.
 * Features a clickable gallery that opens a Modal (Lightbox) with multiple images per project.
 */
export default function Portfolio() {
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [projectsList, setProjectsList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Static list of projects to use as robust fallback with exactly the 6 defined categories
  const fallbackProjects = [
    {
      id: 1,
      title: 'Cozinha Gourmet Anthracite',
      category: 'Cozinha',
      mainImage: 'https://images.unsplash.com/photo-1556911223-e1534ecdb531?auto=format&fit=crop&q=80&w=1200',
      album: [
        'https://images.unsplash.com/photo-1556911223-e1534ecdb531?auto=format&fit=crop&q=80&w=1200',
        'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&q=80&w=1200',
        'https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&q=80&w=1200'
      ],
      description: 'Cozinha com acabamento em tons escuros, ilha central e ferragens alemãs de alta performance.'
    },
    {
      id: 2,
      title: 'Suíte Master Walk-in',
      category: 'Closet',
      mainImage: 'https://images.unsplash.com/photo-1595428774751-267868770857?auto=format&fit=crop&q=80&w=1200',
      album: [
        'https://images.unsplash.com/photo-1595428774751-267868770857?auto=format&fit=crop&q=80&w=1200',
        'https://images.unsplash.com/photo-1592075103427-4c4f346048d0?auto=format&fit=crop&q=80&w=1200'
      ],
      description: 'Closet planejado com divisões inteligentes, iluminação em LED embutida e nichos para calçados.'
    },
    {
      id: 3,
      title: 'Home Office Executivo',
      category: 'Quarto',
      mainImage: 'https://images.unsplash.com/photo-1518481612222-68bbe828ecd1?auto=format&fit=crop&q=80&w=1200',
      album: [
        'https://images.unsplash.com/photo-1518481612222-68bbe828ecd1?auto=format&fit=crop&q=80&w=1200',
        'https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&q=80&w=1200'
      ],
      description: 'Ambiente focado em produtividade com mesa em L, painéis ripados e armários para organização.'
    },
    {
      id: 4,
      title: 'Living Integrado',
      category: 'Sala',
      mainImage: 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&q=80&w=1200',
      album: [
        'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&q=80&w=1200',
        'https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&q=80&w=1200'
      ],
      description: 'Painel de TV com fundo em pedra e móveis suspensos em laca branca fosca.'
    },
    {
      id: 5,
      title: 'Adega Gourmet Climatizada',
      category: 'Adega',
      mainImage: 'https://images.unsplash.com/photo-1560185007-c5ca9d2c014d?auto=format&fit=crop&q=80&w=1200',
      album: [
        'https://images.unsplash.com/photo-1560185007-c5ca9d2c014d?auto=format&fit=crop&q=80&w=1200'
      ],
      description: 'Churrasqueira integrada com marcenaria naval e linda adega para vinhos selecionados.'
    },
    {
      id: 6,
      title: 'Banheiro Spa',
      category: 'Banheiro',
      mainImage: 'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&q=80&w=1200',
      album: [
        'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&q=80&w=1200'
      ],
      description: 'Gabinete suspenso com gavetões e espelheira com moldura em metal.'
    }
  ];

  useEffect(() => {
    fetch('/api/projects')
      .then((res) => {
        if (!res.ok) throw new Error('Falha ao obter lista de projetos');
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setProjectsList(data);
        } else {
          setProjectsList(fallbackProjects);
        }
      })
      .catch((err) => {
        console.warn('Erro ao carregar projetos, usando fallback do sistema:', err);
        setProjectsList(fallbackProjects);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const openModal = (project: any) => {
    setSelectedProject(project);
    setCurrentImageIndex(0);
    // Disable scroll when modal is open
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    setSelectedProject(null);
    document.body.style.overflow = 'auto';
  };

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedProject) {
      setCurrentImageIndex((prev) => (prev + 1) % selectedProject.album.length);
    }
  };

  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedProject) {
      setCurrentImageIndex((prev) => (prev - 1 + selectedProject.album.length) % selectedProject.album.length);
    }
  };

  return (
    <section id="portfolio" className="py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <span className="text-red-800 font-bold uppercase tracking-widest text-sm">Portfólio</span>
          <h2 className="text-4xl md:text-5xl font-bold mt-4 mb-6 tracking-tight text-gray-900">
            Nossos Projetos <span className="text-gray-400 font-light">Realizados</span>
          </h2>
          <p className="max-w-2xl mx-auto text-gray-600 text-lg">
            Clique em um projeto para ver mais detalhes e o álbum completo de fotos.
          </p>
        </div>

        {/* Loading Indicator */}
        {loading ? (
          <div className="flex justify-center items-center py-24">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-800"></div>
          </div>
        ) : projectsList.length === 0 ? (
          <div className="text-center py-24 text-gray-400">
            <p className="text-sm font-medium">Nenhum projeto encontrado.</p>
          </div>
        ) : (
          /* Grid Layout */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {projectsList.map((project, index) => {
              const photoCount = project.album ? project.album.length : 1;
              return (
                <motion.div
                  key={project.id || index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  onClick={() => openModal(project)}
                  className="group relative overflow-hidden rounded-3xl bg-neutral-950 shadow-md hover:shadow-2xl transition-all duration-500 cursor-pointer aspect-[4/3] w-full"
                >
                  {/* Image Container */}
                  <div className="w-full h-full overflow-hidden absolute inset-0">
                    <img
                      src={project.mainImage}
                      alt={project.title}
                      className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                      referrerPolicy="no-referrer"
                    />
                  </div>

                  {/* Premium Black Bottom-Focused Gradient Overlay on Hover */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/35 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-6 z-20">
                    <div className="flex justify-between items-end gap-4 w-full transform translate-y-3 group-hover:translate-y-0 transition-transform duration-300 ease-out">
                      {/* Left Side: Environment/Project Title (Top, tiny) & Category (Bottom, smaller than original title font) */}
                      <div className="min-w-0 flex-1">
                        <span className="text-red-500 text-[9px] sm:text-[10px] font-extrabold tracking-widest block mb-1 uppercase truncate">
                          {project.title}
                        </span>
                        <h3 className="text-white text-base sm:text-lg md:text-xl font-extrabold tracking-tight truncate leading-tight">
                          {project.category}
                        </h3>
                      </div>

                      {/* Right Side: Circular expand button */}
                      <div className="shrink-0">
                        <div className="w-10 h-10 bg-neutral-950/60 border border-white/10 hover:border-red-800 text-white rounded-full flex items-center justify-center transition-all duration-300 ease-out group-hover:bg-red-800 group-hover:scale-105 shadow-md">
                          <Maximize2 size={16} className="text-white" />
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Lightbox Modal */}
      <AnimatePresence>
        {selectedProject && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeModal}
            className="fixed inset-0 z-[100] bg-black/95 flex flex-col items-center justify-center p-4 md:p-10 backdrop-blur-md"
          >
            {/* Close Button */}
            <button
              onClick={closeModal}
              className="absolute top-6 right-6 text-white/50 hover:text-white transition-colors z-[110]"
            >
              <X size={40} />
            </button>

            {/* Main Modal Content */}
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="relative max-w-6xl w-full flex flex-col items-center"
            >
              <div className="relative w-full aspect-video md:h-[70vh] flex items-center justify-center overflow-hidden rounded-xl shadow-2xl bg-black">
                {/* Navigation Arrows if album has more than 1 image */}
                {selectedProject.album.length > 1 && (
                  <>
                    <button
                      onClick={prevImage}
                      className="absolute left-4 p-3 bg-black/50 hover:bg-red-800 text-white rounded-full transition-all z-10"
                    >
                      <ChevronLeft size={30} />
                    </button>
                    <button
                      onClick={nextImage}
                      className="absolute right-4 p-3 bg-black/50 hover:bg-red-800 text-white rounded-full transition-all z-10"
                    >
                      <ChevronRight size={30} />
                    </button>
                  </>
                )}

                {/* Main Image */}
                <img
                  key={currentImageIndex}
                  src={selectedProject.album[currentImageIndex]}
                  alt={selectedProject.title}
                  className="max-h-full max-w-full object-contain"
                  referrerPolicy="no-referrer"
                />
              </div>

              {/* Project Details below Image */}
              <div className="mt-8 text-center text-white max-w-2xl px-4">
                <span className="text-red-600 font-bold uppercase tracking-widest text-xs mb-2 block">
                  {selectedProject.category} • Foto {currentImageIndex + 1} de {selectedProject.album.length}
                </span>
                <h3 className="text-3xl font-bold mb-4">{selectedProject.title}</h3>
                <p className="text-gray-400 text-lg italic">
                  {selectedProject.description}
                </p>
                <a 
                  href="#contato"
                  onClick={closeModal}
                  className="inline-block mt-8 bg-red-800 hover:bg-red-900 text-white px-8 py-3 rounded-full font-bold transition-all"
                >
                  Gostou? Peça um igual
                </a>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
