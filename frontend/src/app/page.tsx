import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-clay-50 flex flex-col items-center justify-center relative overflow-hidden">
      {/* 背景纹理 */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <div className="relative z-10 text-center">
        <div className="w-20 h-20 rounded-full bg-celadon-100 flex items-center justify-center mx-auto mb-8">
          <span className="text-celadon-600 text-3xl font-display">医</span>
        </div>

        <h1 className="font-display text-5xl text-clay-700 mb-4">民医智问</h1>
        <p className="text-clay-400 text-lg mb-2">Ethno Med AI</p>
        <p className="text-clay-300 max-w-md mx-auto mb-12 leading-relaxed">
          融合藏族、羌族、彝族千年医药智慧，
          <br />
          以人工智能技术传承与发扬民族医学。
        </p>

        <Link
          href="/chat"
          className="inline-flex items-center px-8 py-3.5 bg-clay-500 text-white rounded-xl hover:bg-clay-600 transition-all duration-300 shadow-lg shadow-clay-500/20 hover:shadow-clay-500/30 font-medium"
        >
          开始问诊
          <svg
            className="ml-2 w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Link>

        <div className="flex gap-8 mt-16 text-sm text-clay-400">
          <div className="text-center">
            <div className="font-display text-2xl text-clay-600">藏</div>
            <div className="mt-1">藏族医药</div>
          </div>
          <div className="text-center">
            <div className="font-display text-2xl text-clay-600">羌</div>
            <div className="mt-1">羌族医药</div>
          </div>
          <div className="text-center">
            <div className="font-display text-2xl text-clay-600">彝</div>
            <div className="mt-1">彝族医药</div>
          </div>
        </div>
      </div>
    </main>
  );
}
