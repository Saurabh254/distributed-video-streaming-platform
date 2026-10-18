export interface InitiateUploadPayload {
  title: string;
  description?: string;
  category?: string;
  filename: string;
  contentType: string;
  fileSize: number;
}

export interface InitiateUploadResponse {
  video_id: string;
  upload_url: string;
  s3_key: string;
  s3_bucket: string;
  expires_in: number;
}

export interface UploadedVideo {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  category: string | null;
  original_filename: string;
  content_type: string;
  file_size: number;
  s3_bucket: string;
  s3_key: string;
  status: string;
  created_at: string;
  updated_at: string;
  uploaded_at: string | null;
}

export class VideoUploadError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "VideoUploadError";
    this.status = status;
  }
}

/**
 * Request a presigned S3 upload URL through the Next.js API Gateway.
 */
export async function initiateVideoUpload(
  payload: InitiateUploadPayload
): Promise<InitiateUploadResponse> {
  const res = await fetch("/api/videos/upload-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new VideoUploadError(
      errorData.detail || "Failed to initiate video upload",
      res.status
    );
  }

  return await res.json();
}

/**
 * Upload binary file directly to S3 / MinIO via presigned PUT URL with real-time progress callback.
 */
export function uploadBinaryToPresignedUrl(
  uploadUrl: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", file.type);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event: ProgressEvent) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        if (onProgress) onProgress(100);
        resolve();
      } else {
        reject(
          new VideoUploadError(
            `Direct storage upload failed with status ${xhr.status} ${xhr.statusText}`,
            xhr.status
          )
        );
      }
    };

    xhr.onerror = () => {
      reject(
        new VideoUploadError(
          "Direct storage upload failed due to a network error or CORS restriction"
        )
      );
    };

    xhr.onabort = () => {
      reject(new VideoUploadError("Upload was aborted"));
    };

    xhr.send(file);
  });
}

/**
 * Notify the video service that the binary upload is complete and verify storage.
 */
export async function completeVideoUpload(
  videoId: string,
  clientDurationSeconds?: number
): Promise<UploadedVideo> {
  const res = await fetch(`/api/videos/${videoId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_duration_seconds: clientDurationSeconds ?? null,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new VideoUploadError(
      errorData.detail || "Failed to confirm upload completion",
      res.status
    );
  }

  return await res.json();
}
