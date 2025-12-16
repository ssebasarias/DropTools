import React, { useState, useEffect, useRef } from 'react';
import { Image } from 'lucide-react';

const LazyImage = ({ src, alt, className, style, placeholderColor = '#222' }) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const [isInView, setIsInView] = useState(false);
    const imgRef = useRef();

    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                setIsInView(true);
                observer.disconnect();
            }
        });

        if (imgRef.current) {
            observer.observe(imgRef.current);
        }

        return () => {
            if (observer) observer.disconnect();
        };
    }, []);

    return (
        <div
            ref={imgRef}
            className={className}
            style={{
                ...style,
                backgroundColor: placeholderColor,
                position: 'relative',
                overflow: 'hidden',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}
        >
            {!isLoaded && isInView && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Image size={20} color="#444" className="animate-pulse" />
                </div>
            )}

            {isInView && (
                <img
                    src={src}
                    alt={alt}
                    style={{
                        ...style,
                        opacity: isLoaded ? 1 : 0,
                        transition: 'opacity 0.3s ease-in-out',
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover'
                    }}
                    onLoad={() => setIsLoaded(true)}
                />
            )}

            <style>{`
                .animate-pulse {
                    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: .5; }
                }
            `}</style>
        </div>
    );
};

export default LazyImage;
