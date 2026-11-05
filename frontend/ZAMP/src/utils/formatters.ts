export function maskAccountNumber(accountNumber: string): string {
  if (!accountNumber) return '';
  const trimmed = accountNumber.trim();
  if (trimmed.length <= 4) return '•••• ' + trimmed;
  const last4 = trimmed.slice(-4);
  const maskedPortion = '•'.repeat(Math.max(trimmed.length - 4, 8));
  // Group into blocks of 4
  const formatted = maskedPortion.replace(/(.{4})/g, '$1 ').trim();
  return `${formatted} ${last4}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function generateReferenceNumber(): string {
  const year = new Date().getFullYear();
  const randomSuffix = Math.floor(10000 + Math.random() * 90000);
  return `VND-${year}-${randomSuffix}`;
}

