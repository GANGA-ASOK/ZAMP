import type { FC } from 'react';
import { useState } from 'react';
import {
  CaretDown,
  PencilSimple,
  Buildings,
  User,
  Receipt,
  Bank,
  Files,
  CheckCircle,
} from '@phosphor-icons/react';
import type { VendorFormData } from '../../types/vendor';
import { maskAccountNumber } from '../../utils/formatters';

interface ReviewSummaryProps {
  formData: VendorFormData;
  onEditStep: (stepNumber: number) => void;
}

export const ReviewSummary: FC<ReviewSummaryProps> = ({
  formData,
  onEditStep,
}) => {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    company: true,
    contact: false,
    tax: false,
    banking: false,
    documents: false,
  });

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const { company, contact, taxBanking, documents } = formData;
  const uploadedDocCount = Object.keys(documents.documents).length + documents.otherFiles.length;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
      <div className="p-4 sm:p-5 bg-slate-50/80 border-b border-slate-200/80 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">
            Application Review Summary
          </h3>
          <p className="text-xs text-slate-500">
            Verify all details before submitting for official verification
          </p>
        </div>
        <span className="text-xs font-medium text-[#1F211F] bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200/60">
          Ready to review
        </span>
      </div>

      <div className="divide-y divide-slate-100">
        {/* 1. Company Information */}
        <div>
          <div
            onClick={() => toggleSection('company')}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 transition-colors select-none"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#1F211F] flex items-center justify-center">
                <Buildings size={18} weight="bold" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                  1. Company Information
                </h4>
                <p className="text-xs text-slate-500 truncate max-w-xs sm:max-w-md">
                  {company.legalCompanyName || 'Not provided'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditStep(1);
                }}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-medium text-[#1F211F] hover:bg-blue-50 border border-blue-200/60 transition-colors cursor-pointer"
              >
                <PencilSimple size={13} weight="bold" />
                <span>Edit</span>
              </button>
              <div className="text-slate-400">
                <CaretDown
                  size={16}
                  weight="bold"
                  className={`transition-transform duration-200 ${
                    openSections.company ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {openSections.company && (
            <div className="px-5 pb-4 pt-1 bg-slate-50/40 text-xs grid grid-cols-1 sm:grid-cols-2 gap-3 border-t border-slate-100 animate-fadeIn">
              <div>
                <span className="text-slate-400">Legal Name:</span>{' '}
                <span className="font-medium text-slate-800">{company.legalCompanyName || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Trade Name:</span>{' '}
                <span className="font-medium text-slate-800">{company.tradeName || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Entity Type:</span>{' '}
                <span className="font-medium text-slate-800">{company.businessEntityType || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Industry:</span>{' '}
                <span className="font-medium text-slate-800">{company.industry || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Reg. Number (CIN):</span>{' '}
                <span className="font-medium text-slate-800">{company.registrationNumber || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Date of Incorp:</span>{' '}
                <span className="font-medium text-slate-800">{company.incorporationDate || '—'}</span>
              </div>
              <div className="sm:col-span-2">
                <span className="text-slate-400">Registered Address:</span>{' '}
                <span className="font-medium text-slate-800">
                  {company.registeredAddress}, {company.registeredCity}, {company.registeredState} - {company.registeredPincode} ({company.country})
                </span>
              </div>
            </div>
          )}
        </div>

        {/* 2. Contact Information */}
        <div>
          <div
            onClick={() => toggleSection('contact')}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 transition-colors select-none"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <User size={18} weight="bold" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                  2. Contact Information
                </h4>
                <p className="text-xs text-slate-500 truncate max-w-xs sm:max-w-md">
                  {contact.primaryFirstName} {contact.primaryLastName} ({contact.primaryEmail || 'Not provided'})
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditStep(2);
                }}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-medium text-[#1F211F] hover:bg-blue-50 border border-blue-200/60 transition-colors cursor-pointer"
              >
                <PencilSimple size={13} weight="bold" />
                <span>Edit</span>
              </button>
              <div className="text-slate-400">
                <CaretDown
                  size={16}
                  weight="bold"
                  className={`transition-transform duration-200 ${
                    openSections.contact ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {openSections.contact && (
            <div className="px-5 pb-4 pt-1 bg-slate-50/40 text-xs grid grid-cols-1 sm:grid-cols-2 gap-3 border-t border-slate-100 animate-fadeIn">
              <div>
                <span className="text-slate-400">Primary Contact:</span>{' '}
                <span className="font-medium text-slate-800">
                  {contact.primaryFirstName} {contact.primaryLastName} ({contact.primaryDesignation || '—'})
                </span>
              </div>
              <div>
                <span className="text-slate-400">Email:</span>{' '}
                <span className="font-medium text-slate-800">{contact.primaryEmail || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Mobile:</span>{' '}
                <span className="font-medium text-slate-800">{contact.primaryMobile || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Department:</span>{' '}
                <span className="font-medium text-slate-800">{contact.primaryDepartment || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Authorized Signatory:</span>{' '}
                <span className="font-medium text-slate-800">
                  {contact.signatoryName || '—'} ({contact.signatoryDesignation || '—'})
                </span>
              </div>
              <div>
                <span className="text-slate-400">Signatory Email:</span>{' '}
                <span className="font-medium text-slate-800">{contact.signatoryEmail || '—'}</span>
              </div>
            </div>
          )}
        </div>

        {/* 3. Tax Information */}
        <div>
          <div
            onClick={() => toggleSection('tax')}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 transition-colors select-none"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-sky-50 text-[#1F211F] flex items-center justify-center">
                <Receipt size={18} weight="bold" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                  3. Tax Information
                </h4>
                <p className="text-xs text-slate-500">
                  PAN: {taxBanking.panNumber || '—'} • GST: {taxBanking.gstStatus}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditStep(3);
                }}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-medium text-[#1F211F] hover:bg-blue-50 border border-blue-200/60 transition-colors cursor-pointer"
              >
                <PencilSimple size={13} weight="bold" />
                <span>Edit</span>
              </button>
              <div className="text-slate-400">
                <CaretDown
                  size={16}
                  weight="bold"
                  className={`transition-transform duration-200 ${
                    openSections.tax ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {openSections.tax && (
            <div className="px-5 pb-4 pt-1 bg-slate-50/40 text-xs grid grid-cols-1 sm:grid-cols-2 gap-3 border-t border-slate-100 animate-fadeIn">
              <div>
                <span className="text-slate-400">PAN Number:</span>{' '}
                <span className="font-mono font-semibold text-slate-800">{taxBanking.panNumber || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">GST Status:</span>{' '}
                <span className="font-medium text-slate-800">{taxBanking.gstStatus}</span>
              </div>
              {taxBanking.gstStatus === 'Registered' && (
                <>
                  <div>
                    <span className="text-slate-400">GSTIN:</span>{' '}
                    <span className="font-mono font-semibold text-slate-800">{taxBanking.gstin || '—'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">GST State:</span>{' '}
                    <span className="font-medium text-slate-800">{taxBanking.gstState || '—'}</span>
                  </div>
                </>
              )}
              <div>
                <span className="text-slate-400">TAN Number:</span>{' '}
                <span className="font-mono font-semibold text-slate-800">{taxBanking.tanNumber || '—'}</span>
              </div>
            </div>
          )}
        </div>

        {/* 4. Banking Information */}
        <div>
          <div
            onClick={() => toggleSection('banking')}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 transition-colors select-none"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Bank size={18} weight="bold" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                  4. Banking Information
                </h4>
                <p className="text-xs text-slate-500">
                  {taxBanking.bankName || 'Bank'} • {maskAccountNumber(taxBanking.accountNumber)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditStep(3);
                }}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-medium text-[#1F211F] hover:bg-blue-50 border border-blue-200/60 transition-colors cursor-pointer"
              >
                <PencilSimple size={13} weight="bold" />
                <span>Edit</span>
              </button>
              <div className="text-slate-400">
                <CaretDown
                  size={16}
                  weight="bold"
                  className={`transition-transform duration-200 ${
                    openSections.banking ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {openSections.banking && (
            <div className="px-5 pb-4 pt-1 bg-slate-50/40 text-xs grid grid-cols-1 sm:grid-cols-2 gap-3 border-t border-slate-100 animate-fadeIn">
              <div>
                <span className="text-slate-400">Account Holder:</span>{' '}
                <span className="font-medium text-slate-800">{taxBanking.accountHolderName || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Bank Name:</span>{' '}
                <span className="font-medium text-slate-800">{taxBanking.bankName || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Account Number:</span>{' '}
                <span className="font-mono font-semibold text-slate-800">
                  {maskAccountNumber(taxBanking.accountNumber)}
                </span>
              </div>
              <div>
                <span className="text-slate-400">IFSC Code:</span>{' '}
                <span className="font-mono font-semibold text-slate-800">{taxBanking.ifscCode || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Account Type:</span>{' '}
                <span className="font-medium text-slate-800">{taxBanking.accountType || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400">Branch:</span>{' '}
                <span className="font-medium text-slate-800">{taxBanking.bankBranch || '—'}</span>
              </div>
            </div>
          )}
        </div>

        {/* 5. Uploaded Documents */}
        <div>
          <div
            onClick={() => toggleSection('documents')}
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 transition-colors select-none"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
                <Files size={18} weight="bold" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                  5. Uploaded Documents
                </h4>
                <p className="text-xs text-slate-500">
                  {uploadedDocCount} document{uploadedDocCount === 1 ? '' : 's'} attached
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <div className="text-slate-400">
                <CaretDown
                  size={16}
                  weight="bold"
                  className={`transition-transform duration-200 ${
                    openSections.documents ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {openSections.documents && (
            <div className="px-5 pb-4 pt-1 bg-slate-50/40 text-xs border-t border-slate-100 animate-fadeIn space-y-2">
              {uploadedDocCount === 0 ? (
                <p className="text-slate-400 italic">No documents uploaded yet.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {Object.entries(documents.documents).map(([key, doc]) => (
                    <div
                      key={key}
                      className="flex items-center space-x-2 p-2 rounded-lg bg-white border border-slate-200/80"
                    >
                      <CheckCircle size={14} weight="fill" className="text-emerald-500 shrink-0" />
                      <span className="font-medium text-slate-700 truncate">{doc.fileName}</span>
                    </div>
                  ))}
                  {documents.otherFiles.map((doc, idx) => (
                    <div
                      key={idx}
                      className="flex items-center space-x-2 p-2 rounded-lg bg-white border border-slate-200/80"
                    >
                      <CheckCircle size={14} weight="fill" className="text-emerald-500 shrink-0" />
                      <span className="font-medium text-slate-700 truncate">{doc.fileName}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
