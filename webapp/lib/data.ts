import { Video, Comment, EdgeMetric } from "./types";

export const CATEGORIES = [
  "All",
  "Distributed Systems",
  "Transcoding & AV1",
  "Edge Architecture",
  "Low Latency HLS",
  "Cloud Infrastructure",
  "Cinema & 4K",
  "Live Events",
];

export const MOCK_VIDEOS: Video[] = [
  {
    id: "v-distributed-transcoding",
    title: "Building an Ultra-Low Latency Transcoding Pipeline with Ray & FFmpeg",
    description:
      "A deep dive into horizontally scaled distributed chunking, zero-copy memory transfers, and adaptive bitrate manifest generation under 80ms latency. We explore worker node orchestration, dynamic GPU task routing, and failover topologies across multi-region clusters.",
    thumbnail:
      "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80",
    videoUrl:
      "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
    duration: "18:42",
    durationSeconds: 1122,
    views: 142800,
    uploadedAt: "2 hours ago",
    likes: 12450,
    channel: {
      name: "Distributed Core Labs",
      handle: "@dist-core",
      avatar:
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=160&h=160&q=80",
      subscribers: "84.2K",
      verified: true,
    },
    category: "Distributed Systems",
    resolution: "4K",
    codec: "AV1 / opus",
    bitrate: "9,420 kbps",
    fps: 60,
    isLive: false,
    edgePoP: "Edge-US-East (iad-04)",
    tags: ["#distributed", "#transcoding", "#ray", "#ffmpeg", "#lowlatency"],
    chapters: [
      { time: "00:00", title: "Architecture Blueprint" },
      { time: "03:15", title: "Chunk Ingestion & Kafka Ring" },
      { time: "08:40", title: "NVENC Hardware Acceleration" },
      { time: "14:10", title: "HLS Manifest Stitching" },
      { time: "17:00", title: "Edge Benchmark Results" },
    ],
  },
  {
    id: "v-webrtc-mesh",
    title: "WebRTC vs HLS at 10 Million Concurrent Edge Viewers",
    description:
      "Analyzing cost structures, segment buffer sizing, packet loss mitigation via Forward Error Correction (FEC), and hybrid P2P mesh offload strategies at internet-scale live events.",
    thumbnail:
      "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
    videoUrl:
      "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    duration: "24:19",
    durationSeconds: 1459,
    views: 98400,
    uploadedAt: "1 day ago",
    likes: 8120,
    channel: {
      name: "Aether Systems",
      handle: "@aether_sys",
      avatar:
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=160&h=160&q=80",
      subscribers: "128K",
      verified: true,
    },
    category: "Low Latency HLS",
    resolution: "4K",
    codec: "H.265 / aac",
    bitrate: "8,100 kbps",
    fps: 60,
    isLive: false,
    edgePoP: "Edge-EU-West (fra-02)",
    tags: ["#webrtc", "#streaming", "#cdn", "#p2p"],
    chapters: [
      { time: "00:00", title: "Introduction & Latency Tax" },
      { time: "05:22", title: "Sub-second HLS Chunking" },
      { time: "12:50", title: "Global CDN Edge Caching" },
      { time: "19:30", title: "Cost & Bandwidth Efficiency" },
    ],
  },
  {
    id: "v-edge-compute",
    title: "Edge Caching Algorithms: Pushing Video 1ms from User Eyes",
    description:
      "How Anycast routing, eBPF packet acceleration, and cache-hit hierarchies reduce buffering to zero for distributed video playback across 120 global Points of Presence.",
    thumbnail:
      "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80",
    videoUrl:
      "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    duration: "15:08",
    durationSeconds: 908,
    views: 65200,
    uploadedAt: "3 days ago",
    likes: 4930,
    channel: {
      name: "InfraPulse",
      handle: "@infrapulse",
      avatar:
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=160&h=160&q=80",
      subscribers: "45.1K",
      verified: false,
    },
    category: "Edge Architecture",
    resolution: "1440p",
    codec: "AV1 / opus",
    bitrate: "6,500 kbps",
    fps: 60,
    isLive: false,
    edgePoP: "Edge-APAC (nrt-01)",
    tags: ["#edge", "#ebpf", "#anycast", "#caching"],
  },
  {
    id: "v-cinema-hdr",
    title: "Cinematic 4K 60FPS: HDR10 Master Stream Demonstration",
    description:
      "Visual dynamic range demonstration benchmark testing color grading fidelity, 10-bit depth banding elimination, and perceptual quantization in real-time streaming.",
    thumbnail:
      "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=1200&q=80",
    videoUrl:
      "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
    duration: "12:35",
    durationSeconds: 755,
    views: 312000,
    uploadedAt: "5 days ago",
    likes: 27900,
    channel: {
      name: "Chroma Studio",
      handle: "@chroma_film",
      avatar:
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=160&h=160&q=80",
      subscribers: "210K",
      verified: true,
    },
    category: "Cinema & 4K",
    resolution: "4K",
    codec: "VP9 / vorbis",
    bitrate: "12,800 kbps",
    fps: 60,
    isLive: false,
    edgePoP: "Edge-US-West (sfo-01)",
    tags: ["#hdr10", "#4k", "#colorgrade", "#cinema"],
  },
  {
    id: "v-live-cluster",
    title: "LIVE: Kubernetes Pod Autoscaling Under Flash-Crowd Surge",
    description:
      "Real-time chaos engineering test stream. Simulating 500,000 artificial viewers hitting the transcoding ingest gateways simultaneously with Grafana telemetry dashboards.",
    thumbnail:
      "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
    videoUrl:
      "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    duration: "LIVE",
    durationSeconds: 0,
    views: 4210,
    uploadedAt: "Started 45m ago",
    likes: 1820,
    channel: {
      name: "SRE Ops Network",
      handle: "@sre_ops",
      avatar:
        "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=160&h=160&q=80",
      subscribers: "39.8K",
      verified: true,
    },
    category: "Cloud Infrastructure",
    resolution: "1080p",
    codec: "H.264 / aac",
    bitrate: "4,500 kbps",
    fps: 60,
    isLive: true,
    edgePoP: "Edge-US-Central (ord-02)",
    tags: ["#kubernetes", "#autoscaling", "#chaosengineering", "#live"],
  },
  {
    id: "v-av1-benchmark",
    title: "AV1 vs HEVC vs VVC: Comprehensive Efficiency Benchmark in 2026",
    description:
      "Comparative visual metric analysis including VMAF, SSIM, and PSNR at bitrates ranging from 1 Mbps to 25 Mbps. Hardware decoder availability metrics across mobile and television hardware.",
    thumbnail:
      "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80",
    videoUrl:
      "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    duration: "21:10",
    durationSeconds: 1270,
    views: 74300,
    uploadedAt: "1 week ago",
    likes: 5410,
    channel: {
      name: "Codec Foundation",
      handle: "@codecfdn",
      avatar:
        "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=160&h=160&q=80",
      subscribers: "58.9K",
      verified: true,
    },
    category: "Transcoding & AV1",
    resolution: "4K",
    codec: "AV1 / opus",
    bitrate: "8,800 kbps",
    fps: 60,
    isLive: false,
    edgePoP: "Edge-EU-North (arn-01)",
    tags: ["#av1", "#codecs", "#vmaf", "#efficiency"],
  },
];

export const MOCK_COMMENTS: Comment[] = [
  {
    id: "c1",
    author: "Elena Rostova",
    handle: "@elena_systems",
    avatar:
      "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&h=120&q=80",
    content:
      "The zero-copy ring buffer implementation in Go with shared memory segments reduced our cluster CPU usage by nearly 42%. Fantastic explanation around minute 8!",
    timestamp: "2 hours ago",
    likes: 142,
    isLiked: false,
  },
  {
    id: "c2",
    author: "Marcus Vance",
    handle: "@mvance_dev",
    avatar:
      "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=120&h=120&q=80",
    content:
      "Are you utilizing CMAF chunks with chunked transfer encoding (CTE) to achieve the sub-80ms segment delivery, or pure WebRTC data channels for control messages?",
    timestamp: "4 hours ago",
    likes: 89,
    isLiked: true,
  },
  {
    id: "c3",
    author: "Amina Al-Mansoor",
    handle: "@amina_cloud",
    avatar:
      "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=120&h=120&q=80",
    content:
      "This is textbook distributed architecture. The telemetry HUD in this player is also so sleek! Would love to see an episode on eBPF packet sniffing for dropped keyframes.",
    timestamp: "12 hours ago",
    likes: 54,
    isLiked: false,
  },
];

export const EDGE_NODES: EdgeMetric[] = [
  {
    location: "US East (N. Virginia)",
    region: "iad-04",
    latencyMs: 14,
    status: "optimal",
    activeStreams: 4210,
    bandwidthGbps: 342.5,
  },
  {
    location: "US West (San Jose)",
    region: "sjc-01",
    latencyMs: 18,
    status: "optimal",
    activeStreams: 3120,
    bandwidthGbps: 280.1,
  },
  {
    location: "Europe West (Frankfurt)",
    region: "fra-02",
    latencyMs: 22,
    status: "optimal",
    activeStreams: 2890,
    bandwidthGbps: 245.8,
  },
  {
    location: "Asia Pacific (Tokyo)",
    region: "nrt-01",
    latencyMs: 31,
    status: "optimal",
    activeStreams: 3450,
    bandwidthGbps: 310.2,
  },
  {
    location: "South America (São Paulo)",
    region: "gru-01",
    latencyMs: 54,
    status: "nominal",
    activeStreams: 1120,
    bandwidthGbps: 98.4,
  },
];
