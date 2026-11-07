import type { FC } from 'react';
import { FormInput } from '../components/common/FormInput';
import { FormSelect } from '../components/common/FormSelect';
import { FormTextarea } from '../components/common/FormTextarea';
import { FormCheckbox } from '../components/common/FormCheckbox';
import type {
  CompanyInformationData,
  FormValidationErrors,
} from '../types/vendor';
import {
  INDIAN_STATES,
  INDUSTRIES,
} from '../utils/validation';

const ENTITY_TYPES = [
  'Private Limited Company',
  'Public Limited Company',
  'Limited Liability Partnership (LLP)',
  'Partnership',
  'Sole Proprietorship',
  'One Person Company (OPC)',
  'Other',
];

const COUNTRIES = [
  'India',
  'United States',
  'United Kingdom',
  'Singapore',
  'United Arab Emirates',
  'Germany',
  'Canada',
  'Australia',
  'Other',
];

interface Step1CompanyInfoProps {
  data: CompanyInformationData;
  errors: FormValidationErrors;
  onChange: (field: keyof CompanyInformationData, value: unknown) => void;
}

export const Step1CompanyInfo: FC<Step1CompanyInfoProps> = ({
  data,
  errors,
  onChange,
}) => {
  const requiresCorporateDetails = [
    'Private Limited Company',
    'Public Limited Company',
    'Limited Liability Partnership (LLP)',
    'One Person Company (OPC)',
  ].includes(data.businessEntityType);

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Basic Company Details */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <FormInput
            id="legalCompanyName"
            label="Legal Company Name"
            required
            placeholder="e.g. Acme Technologies Private Limited"
            value={data.legalCompanyName}
            onChange={(e) => onChange('legalCompanyName', e.target.value)}
            error={errors.legalCompanyName}
          />
        </div>

        <div>
          <FormInput
            id="tradeName"
            label="Trade Name / Brand Name"
            placeholder="e.g. Acme Cloud"
            value={data.tradeName}
            onChange={(e) => onChange('tradeName', e.target.value)}
            error={errors.tradeName}
          />
        </div>

        <div>
          <FormSelect
            id="businessEntityType"
            label="Business Entity Type"
            required
            placeholder="Select entity type"
            options={ENTITY_TYPES}
            value={data.businessEntityType}
            onChange={(e) => onChange('businessEntityType', e.target.value)}
            error={errors.businessEntityType}
          />
        </div>

        <div>
          <FormSelect
            id="country"
            label="Country of Registration"
            required
            options={COUNTRIES}
            value={data.country}
            onChange={(e) => onChange('country', e.target.value)}
            error={errors.country}
          />
        </div>

        <div>
          <FormSelect
            id="industry"
            label="Industry"
            required
            placeholder="Select industry"
            options={INDUSTRIES}
            value={data.industry}
            onChange={(e) => onChange('industry', e.target.value)}
            error={errors.industry}
          />
        </div>

        {/* Corporate Details - Required conditionally */}
        {requiresCorporateDetails && (
          <>
            <div>
              <FormInput
                id="registrationNumber"
                label="Registration Number (CIN / LLPIN)"
                required
                placeholder="e.g. U72200KA2021PTC123456"
                value={data.registrationNumber}
                onChange={(e) => onChange('registrationNumber', e.target.value.toUpperCase())}
                error={errors.registrationNumber}
                helperText="Required for corporate entity verification"
              />
            </div>

            <div>
              <FormInput
                id="incorporationDate"
                label="Date of Incorporation"
                type="date"
                required
                value={data.incorporationDate}
                onChange={(e) => onChange('incorporationDate', e.target.value)}
                error={errors.incorporationDate}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>
          </>
        )}

        <div className="sm:col-span-2">
          <FormInput
            id="website"
            label="Company Website"
            type="url"
            placeholder="https://example.com"
            value={data.website}
            onChange={(e) => onChange('website', e.target.value)}
            error={errors.website}
          />
        </div>
      </div>

      {/* Registered Office Address */}
      <div className="pt-2 border-t border-slate-100">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">
          Registered Office Address
        </h3>

        <div className="space-y-4">
          <FormTextarea
            id="registeredAddress"
            label="Registered Address"
            required
            placeholder="Street address, building, suite, or flat number"
            value={data.registeredAddress}
            onChange={(e) => onChange('registeredAddress', e.target.value)}
            error={errors.registeredAddress}
            rows={2}
          />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <FormInput
                id="registeredCity"
                label="City"
                required
                placeholder="e.g. Bengaluru"
                value={data.registeredCity}
                onChange={(e) => onChange('registeredCity', e.target.value)}
                error={errors.registeredCity}
              />
            </div>

            <div>
              {data.country === 'India' ? (
                <FormSelect
                  id="registeredState"
                  label="State"
                  required
                  placeholder="Select state"
                  options={INDIAN_STATES}
                  value={data.registeredState}
                  onChange={(e) => onChange('registeredState', e.target.value)}
                  error={errors.registeredState}
                />
              ) : (
                <FormInput
                  id="registeredState"
                  label="State / Province"
                  required
                  placeholder="State/Province"
                  value={data.registeredState}
                  onChange={(e) => onChange('registeredState', e.target.value)}
                  error={errors.registeredState}
                />
              )}
            </div>

            <div>
              <FormInput
                id="registeredPincode"
                label={data.country === 'India' ? 'PIN Code' : 'Postal Code'}
                required
                placeholder={data.country === 'India' ? '6 digits (e.g. 560001)' : 'Postal code'}
                value={data.registeredPincode}
                onChange={(e) => onChange('registeredPincode', e.target.value)}
                error={errors.registeredPincode}
                maxLength={data.country === 'India' ? 6 : 10}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Operational Address Toggle */}
      <div className="pt-2 border-t border-slate-100 space-y-4">
        <FormCheckbox
          id="isOperationalSameAsRegistered"
          checked={data.isOperationalSameAsRegistered}
          onChange={(checked) => onChange('isOperationalSameAsRegistered', checked)}
          label="Is your operational address the same as your registered office address?"
        />

        {!data.isOperationalSameAsRegistered && (
          <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200/80 space-y-3 animate-fadeIn">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Operational Office Address
            </h4>

            <FormTextarea
              id="operationalAddress"
              label="Operational Address"
              required
              placeholder="Physical office address"
              value={data.operationalAddress}
              onChange={(e) => onChange('operationalAddress', e.target.value)}
              error={errors.operationalAddress}
              rows={2}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <FormInput
                id="operationalCity"
                label="City"
                required
                placeholder="City"
                value={data.operationalCity}
                onChange={(e) => onChange('operationalCity', e.target.value)}
                error={errors.operationalCity}
              />

              {data.country === 'India' ? (
                <FormSelect
                  id="operationalState"
                  label="State"
                  required
                  placeholder="Select state"
                  options={INDIAN_STATES}
                  value={data.operationalState}
                  onChange={(e) => onChange('operationalState', e.target.value)}
                  error={errors.operationalState}
                />
              ) : (
                <FormInput
                  id="operationalState"
                  label="State / Province"
                  required
                  placeholder="State/Province"
                  value={data.operationalState}
                  onChange={(e) => onChange('operationalState', e.target.value)}
                  error={errors.operationalState}
                />
              )}

              <FormInput
                id="operationalPincode"
                label={data.country === 'India' ? 'PIN Code' : 'Postal Code'}
                required
                placeholder="PIN / Postal Code"
                value={data.operationalPincode}
                onChange={(e) => onChange('operationalPincode', e.target.value)}
                error={errors.operationalPincode}
                maxLength={data.country === 'India' ? 6 : 10}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
