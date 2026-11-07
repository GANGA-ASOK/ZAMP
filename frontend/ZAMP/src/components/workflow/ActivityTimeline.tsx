import type { FC } from 'react';
import {
  CheckCircle,
  XCircle,
  WarningCircle,
  Clock,
  ChatCircleDots,
  FileArrowUp,
  Cpu,
  User,
  ShieldCheck,
  NotePencil,
  Sparkle,
} from '@phosphor-icons/react';
import type { ActivityEvent } from '../../services/workflowService';

interface ActivityTimelineProps {
  events: ActivityEvent[];
  emptyMessage?: string;
}

export const ActivityTimeline: FC<ActivityTimelineProps> = ({
  events,
  emptyMessage = 'No activity recorded yet.',
}) => {
  if (!events || events.length === 0) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        <Clock size={24} className="mx-auto mb-2 text-slate-300" />
        <p>{emptyMessage}</p>
      </div>
    );
  }

  const getEventIcon = (type: string, actor: string) => {
    switch (type.toLowerCase()) {
      case 'created':
      case 'draft':
        return <NotePencil size={14} weight="bold" className="text-slate-600" />;
      case 'submitted':
        return <FileArrowUp size={14} weight="bold" className="text-blue-600" />;
      case 'under_review':
        return <Clock size={14} weight="bold" className="text-amber-600" />;
      case 'clarification_requested':
        return <WarningCircle size={14} weight="bold" className="text-amber-600" />;
      case 'clarification_responded':
        return <ChatCircleDots size={14} weight="bold" className="text-blue-600" />;
      case 'resubmitted':
        return <FileArrowUp size={14} weight="bold" className="text-indigo-600" />;
      case 'approved':
        return <CheckCircle size={14} weight="bold" className="text-emerald-600" />;
      case 'rejected':
        return <XCircle size={14} weight="bold" className="text-rose-600" />;
      case 'ai_verification':
        return <Cpu size={14} weight="bold" className="text-purple-600" />;
      case 'comment_added':
        return <ChatCircleDots size={14} weight="bold" className="text-slate-600" />;
      default:
        return actor === 'admin' ? (
          <ShieldCheck size={14} weight="bold" className="text-blue-600" />
        ) : (
          <User size={14} weight="bold" className="text-slate-600" />
        );
    }
  };

  const getActorBadge = (actor: string) => {
    switch (actor.toLowerCase()) {
      case 'admin':
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200/60 inline-flex items-center space-x-1">
            <ShieldCheck size={11} weight="fill" />
            <span>Admin</span>
          </span>
        );
      case 'vendor':
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200/60 inline-flex items-center space-x-1">
            <User size={11} weight="bold" />
            <span>Vendor</span>
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 inline-flex items-center space-x-1">
            <Sparkle size={11} weight="fill" />
            <span>System</span>
          </span>
        );
    }
  };

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
      {events.map((ev, idx) => {
        const formattedDate = new Date(ev.timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });

        return (
          <div key={ev.id || idx} className="relative group">
            {/* Timeline node */}
            <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-white border-2 border-slate-300 group-hover:border-[#07569B] flex items-center justify-center transition-colors shadow-2xs">
              <div className="w-2 h-2 rounded-full bg-slate-400 group-hover:bg-[#07569B]" />
            </div>

            <div className="bg-slate-50/70 hover:bg-white rounded-2xl p-3.5 border border-slate-200/80 transition-all text-xs space-y-1.5 shadow-2xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <div className="p-1 rounded-lg bg-white border border-slate-200/80 text-slate-700">
                    {getEventIcon(ev.event_type, ev.actor_type)}
                  </div>
                  <span className="font-semibold text-slate-900 capitalize">
                    {ev.event_type.replace(/_/g, ' ')}
                  </span>
                  {getActorBadge(ev.actor_type)}
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {formattedDate}
                </span>
              </div>

              <p className="text-slate-600 text-xs pl-7 leading-relaxed">
                {ev.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

