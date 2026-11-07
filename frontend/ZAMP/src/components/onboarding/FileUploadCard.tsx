import type { FC, DragEvent, ChangeEvent } from 'react';
import { useRef, useState } from 'react';
import {
  CloudArrowUp,
  FilePdf,
  FileImage,
  Trash,
  Eye,
  ArrowsClockwise,
  CheckCircle,
  WarningCircle,
} from '@phosphor-icons/react';
import type { UploadedDocInfo } from '../../types/vendor';
import { formatFileSize } from '../../utils/formatters';

interface FileUploadCardProps {
  id: string;
  title: string;
  description: string;
  required?: boolean;
  docInfo?: UploadedDocInfo;
  onFileSelect: (file: File) => void;
  onRemove: () => void;
  onPreview: (doc: UploadedDocInfo) => void;
  error?: string;
  accept?: string;
  maxSizeMB?: number;
}

export const FileUploadCard: FC<FileUploadCardProps> = ({
  id,
  title,
  description,
  required = false,
  docInfo,
  onFileSelect,
  onRemove,
  onPreview,
  error,
  accept = '.pdf,.png,.jpg,.jpeg',
  maxSizeMB = 10,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files[0]);
    }
  };

  const handleFiles = (file: File) => {
    // Check size
    if (file.size > maxSizeMB * 1024 * 1024) {
      alert(`File size exceeds ${maxSizeMB}MB limit.`);
      return;
    }
    // Check type
    const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type) && !/\.(pdf|png|jpe?g)$/i.test(file.name)) {
      alert('Invalid file format. Please upload PDF, PNG, or JPG.');
      return;
    }
    onFileSelect(file);
  };

  const isUploaded = docInfo && docInfo.status === 'completed';
  const isUploading = docInfo && docInfo.status === 'uploading';
  const isPdf = docInfo && (docInfo.fileType === 'application/pdf' || docInfo.fileName.toLowerCase().endsWith('.pdf'));

  return (
    <div
      id={id}
      className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
        error
          ? 'border-red-300 bg-red-50/20'
          : isUploaded
          ? 'border-emerald-200/80 bg-emerald-50/15'
          : isDragOver
          ? 'border-[#1F211F] bg-blue-50/40 shadow-xs'
          : 'border-slate-200 bg-white hover:border-slate-300'
      }`}
    >
      {/* Card Header */}
      <div className="p-4 sm:p-5 flex items-start justify-between border-b border-slate-100/80">
        <div>
          <div className="flex items-center space-x-2">
            <h4 className="text-sm font-semibold text-slate-800">
              {title}
            </h4>
            {required ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-50 text-red-600 border border-red-200/50">
                Required
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-500">
                Optional
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        </div>

        {isUploaded && (
          <span className="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200/60">
            <CheckCircle size={14} weight="fill" />
            <span>Uploaded</span>
          </span>
        )}
      </div>

      {/* Main Content Area */}
      <div className="p-4 sm:p-5">
        <input
          ref={fileInputRef}
          type="file"
          id={`${id}-input`}
          accept={accept}
          onChange={handleFileInputChange}
          className="hidden"
        />

        {isUploaded && docInfo ? (
          /* Uploaded File Item */
          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-slate-50/80 rounded-xl border border-slate-200/80 gap-3">
            <div className="flex items-center space-x-3 overflow-hidden">
              <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center shrink-0 text-[#1F211F]">
                {isPdf ? <FilePdf size={22} weight="bold" /> : <FileImage size={22} weight="bold" />}
              </div>
              <div className="truncate">
                <p className="text-sm font-semibold text-slate-800 truncate">
                  {docInfo.fileName}
                </p>
                <p className="text-xs text-slate-400">
                  {formatFileSize(docInfo.fileSize)} • Ready for verification
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-1 shrink-0 justify-end">
              <button
                type="button"
                onClick={() => onPreview(docInfo)}
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-[#1F211F] hover:bg-white transition-colors cursor-pointer border border-transparent hover:border-slate-200"
                title="Preview document"
              >
                <Eye size={15} />
                <span>Preview</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-[#1F211F] hover:bg-white transition-colors cursor-pointer border border-transparent hover:border-slate-200"
                title="Replace file"
              >
                <ArrowsClockwise size={15} />
                <span>Replace</span>
              </button>

              <button
                type="button"
                onClick={onRemove}
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                title="Remove file"
              >
                <Trash size={15} />
              </button>
            </div>
          </div>
        ) : isUploading && docInfo ? (
          /* Uploading Progress State */
          <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-700 truncate max-w-xs">
                Uploading {docInfo.fileName}...
              </span>
              <span className="font-semibold text-[#1F211F]">{docInfo.progress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-[#1F211F] h-1.5 rounded-full transition-all duration-200 ease-out"
                style={{ width: `${docInfo.progress}%` }}
              />
            </div>
          </div>
        ) : (
          /* Empty / Drag-and-drop zone */
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center ${
              isDragOver
                ? 'border-[#1F211F] bg-blue-50/60'
                : 'border-slate-300 hover:border-[#1F211F]/80 hover:bg-slate-50/60'
            }`}
          >
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mb-2 group-hover:scale-105 transition-transform">
              <CloudArrowUp size={22} weight="bold" />
            </div>
            <p className="text-xs font-medium text-slate-700">
              <span className="text-[#1F211F] font-semibold underline underline-offset-2">
                Click to upload
              </span>{' '}
              or drag and drop
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Accepted formats: PDF, PNG, JPG (Max {maxSizeMB} MB)
            </p>
          </div>
        )}

        {/* Inline Error Message */}
        {error && (
          <div className="mt-2.5 flex items-center space-x-1.5 text-xs text-red-500 animate-fadeIn">
            <WarningCircle size={14} weight="bold" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};
