import type { FC } from 'react';
import { X, FilePdf, FileImage } from '@phosphor-icons/react';
import type { UploadedDocInfo } from '../../types/vendor';
import { formatFileSize } from '../../utils/formatters';

interface FilePreviewModalProps {
  document: UploadedDocInfo | null;
  onClose: () => void;
}

export const FilePreviewModal: FC<FilePreviewModalProps> = ({
  document,
  onClose,
}) => {
  if (!document) return null;

  const isPdf = document.fileType === 'application/pdf' || document.fileName.toLowerCase().endsWith('.pdf');
  const isImage = document.fileType.startsWith('image/') || /\.(png|jpe?g)$/i.test(document.fileName);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-white rounded-[32px] shadow-2xl overflow-hidden border border-slate-100 flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-[#1F211F] flex items-center justify-center">
              {isPdf ? <FilePdf size={20} weight="bold" /> : <FileImage size={20} weight="bold" />}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-800 truncate max-w-xs sm:max-w-md">
                {document.fileName}
              </h3>
              <p className="text-xs text-slate-500">
                {formatFileSize(document.fileSize)} • Uploaded {document.uploadedAt || 'recently'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-200/60 hover:bg-slate-200 text-slate-600 flex items-center justify-center transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X size={16} weight="bold" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 flex flex-col items-center justify-center bg-slate-100/40 min-h-[280px]">
          {isImage && document.previewUrl ? (
            <img
              src={document.previewUrl}
              alt={document.fileName}
              className="max-h-96 max-w-full rounded-xl object-contain border border-slate-200 shadow-sm"
            />
          ) : isPdf ? (
            <div className="flex flex-col items-center justify-center text-center p-8 bg-white rounded-2xl border border-slate-200 shadow-sm max-w-md w-full">
              <div className="w-16 h-16 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center mb-4">
                <FilePdf size={36} weight="bold" />
              </div>
              <h4 className="text-base font-semibold text-slate-800 mb-1">
                PDF Document Preview
              </h4>
              <p className="text-xs text-slate-500 mb-4 max-w-xs">
                {document.fileName} ({formatFileSize(document.fileSize)})
              </p>
              <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 text-left space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Status:</span>
                  <span className="font-semibold text-emerald-600">Verified format</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Integrity:</span>
                  <span className="font-semibold text-slate-700">Checksum valid (Mock)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">MIME Type:</span>
                  <span className="font-mono text-slate-700">application/pdf</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center p-8">
              <FileImage size={48} className="text-slate-400 mb-2" />
              <p className="text-sm font-medium text-slate-700">{document.fileName}</p>
              <p className="text-xs text-slate-400">{formatFileSize(document.fileSize)}</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-100 bg-white flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Document is ready for automated AI verification
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
};
