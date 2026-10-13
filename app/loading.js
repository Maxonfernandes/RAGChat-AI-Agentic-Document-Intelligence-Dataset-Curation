"use client"
const Loading = () => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black z-50 ">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100" height="100">
        <circle fill="#284139" stroke="#284139" strokeWidth="15" r="15" cx="40" cy="100">
          <animate
            attributeName="opacity"
            calcMode="spline"
            dur="2s"
            values="1;0;1;"
            keySplines=".5 0 .5 1;.5 0 .5 1"
            repeatCount="indefinite"
            begin="-.4s"
          />
        </circle>
        <circle fill="#284139" stroke="#284139" strokeWidth="15" r="15" cx="100" cy="100">
          <animate
            attributeName="opacity"
            calcMode="spline"
            dur="2s"
            values="1;0;1;"
            keySplines=".5 0 .5 1;.5 0 .5 1"
            repeatCount="indefinite"
            begin="-.2s"
          />
        </circle>
        <circle fill="#284139" stroke="#284139" strokeWidth="15" r="15" cx="160" cy="100">
          <animate
            attributeName="opacity"
            calcMode="spline"
            dur="2s"
            values="1;0;1;"
            keySplines=".5 0 .5 1;.5 0 .5 1"
            repeatCount="indefinite"
            begin="0s"
          />
        </circle>
      </svg>
    </div>
  );
};

export default Loading;