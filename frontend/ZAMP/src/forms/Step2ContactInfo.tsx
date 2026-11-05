import type { FC } from 'react';
import { FormInput } from '../components/common/FormInput';
import { FormSelect } from '../components/common/FormSelect';
import { FormCheckbox } from '../components/common/FormCheckbox';
import type { ContactInformationData, FormValidationErrors } from '../types/vendor';
import { DEPARTMENTS } from '../utils/validation';

interface Step2ContactInfoProps {
  data: ContactInformationData;
  errors: FormValidationErrors;
  onChange: (field: keyof ContactInformationData, value: unknown) => void;
}

export const Step2ContactInfo: FC<Step2ContactInfoProps> = ({
  data,
  errors,
  onChange,
}) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Primary Contact Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="text-sm font-semibold text-slate-800">
            Primary Contact Person
          </h3>
          <span className="text-xs text-slate-400">Main point of contact</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormInput
            label="First Name"
            required
            placeholder="e.g. Rahul"
            value={data.primaryFirstName}
            onChange={(e) => onChange('primaryFirstName', e.target.value)}
            error={errors.primaryFirstName}
          />

          <FormInput
            label="Last Name"
            required
            placeholder="e.g. Sharma"
            value={data.primaryLastName}
            onChange={(e) => onChange('primaryLastName', e.target.value)}
            error={errors.primaryLastName}
          />

          <FormInput
            label="Designation / Job Title"
            required
            placeholder="e.g. Head of Procurement"
            value={data.primaryDesignation}
            onChange={(e) => onChange('primaryDesignation', e.target.value)}
            error={errors.primaryDesignation}
          />

          <FormSelect
            label="Department"
            required
            placeholder="Select department"
            options={DEPARTMENTS}
            value={data.primaryDepartment}
            onChange={(e) => onChange('primaryDepartment', e.target.value)}
            error={errors.primaryDepartment}
          />

          <FormInput
            label="Business Email Address"
            type="email"
            required
            placeholder="e.g. r.sharma@company.com"
            value={data.primaryEmail}
            onChange={(e) => onChange('primaryEmail', e.target.value)}
            error={errors.primaryEmail}
          />

          <FormInput
            label="Mobile Number"
            type="tel"
            required
            placeholder="e.g. +91 98765 43210"
            value={data.primaryMobile}
            onChange={(e) => onChange('primaryMobile', e.target.value)}
            error={errors.primaryMobile}
          />
        </div>
      </div>

      {/* Authorized Representative Section */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="text-sm font-semibold text-slate-800">
            Authorized Signatory / Representative
          </h3>
          <span className="text-xs text-slate-400">Legal representative</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <FormInput
            label="Signatory Full Name"
            required
            placeholder="e.g. Vikramaditya Rao"
            value={data.signatoryName}
            onChange={(e) => onChange('signatoryName', e.target.value)}
            error={errors.signatoryName}
          />

          <FormInput
            label="Signatory Designation"
            required
            placeholder="e.g. Managing Director"
            value={data.signatoryDesignation}
            onChange={(e) => onChange('signatoryDesignation', e.target.value)}
            error={errors.signatoryDesignation}
          />

          <FormInput
            label="Signatory Email"
            type="email"
            required
            placeholder="e.g. v.rao@company.com"
            value={data.signatoryEmail}
            onChange={(e) => onChange('signatoryEmail', e.target.value)}
            error={errors.signatoryEmail}
          />
        </div>
      </div>

      {/* Secondary Contact (Optional) */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="text-sm font-semibold text-slate-800">
            Secondary Contact <span className="text-xs font-normal text-slate-400">(Optional)</span>
          </h3>
          <span className="text-xs text-slate-400">Alternate backup contact</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <FormInput
            label="Full Name"
            placeholder="e.g. Priya Nair"
            value={data.secondaryName}
            onChange={(e) => onChange('secondaryName', e.target.value)}
            error={errors.secondaryName}
          />

          <FormInput
            label="Email Address"
            type="email"
            placeholder="e.g. priya.n@company.com"
            value={data.secondaryEmail}
            onChange={(e) => onChange('secondaryEmail', e.target.value)}
            error={errors.secondaryEmail}
          />

          <FormInput
            label="Phone Number"
            type="tel"
            placeholder="e.g. +91 98765 43211"
            value={data.secondaryPhone}
            onChange={(e) => onChange('secondaryPhone', e.target.value)}
            error={errors.secondaryPhone}
          />
        </div>
      </div>

      {/* Mandatory Authorization Confirmation */}
      <div className="p-4 rounded-2xl bg-blue-50/60 border border-blue-100">
        <FormCheckbox
          id="confirm-authorized"
          required
          checked={data.confirmAuthorized}
          onChange={(checked) => onChange('confirmAuthorized', checked)}
          label="I confirm that I am authorized to submit this vendor registration application on behalf of the organization."
          error={errors.confirmAuthorized}
        />
      </div>
    </div>
  );
};
