import React from 'react';

const Skeleton = ({ className = '' }) => {
  return (
    <div className={`bg-bg-tertiary animate-pulse rounded ${className}`}></div>
  );
};

export default Skeleton;
