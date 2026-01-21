"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Send, Loader2 } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

export default function Home() {
  const [message, setMessage] = useState("");
  const queryClient = useQueryClient();

  const { data: messagesData, isLoading } = useQuery({
    queryKey: ["messages"],
    queryFn: () => apiClient.getMessages({ page: 1, page_size: 50 }),
  });

  const sendMessageMutation = useMutation({
    mutationFn: (content: string) =>
      apiClient.sendMessage({ content }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["messages"] });
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      setMessage("");

      // Show notification if drafts were created
      if (data.drafts && data.drafts.length > 0) {
        alert(
          `${data.drafts.length}件のタスク案が生成されました。Draftページで確認してください。`
        );
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      sendMessageMutation.mutate(message.trim());
    }
  };

  const messages = messagesData?.items || [];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-xl font-semibold text-gray-900">チャット</h2>
        <p className="text-sm text-gray-500 mt-1">
          タスクを自然な言葉で入力してください
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-500">メッセージはありません</p>
              <p className="text-sm text-gray-400 mt-2">
                例: 「明日までにレポートを完成させる」
              </p>
            </div>
          </div>
        ) : (
          messages.reverse().map((msg) => (
            <div
              key={msg.message_id}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-2xl px-4 py-3 rounded-lg ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-white border border-gray-200 text-gray-900"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                <p
                  className={`text-xs mt-2 ${
                    msg.role === "user"
                      ? "text-blue-100"
                      : "text-gray-400"
                  }`}
                >
                  {format(new Date(msg.created_at), "M月d日 HH:mm", {
                    locale: ja,
                  })}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="タスクを入力..."
            disabled={sendMessageMutation.isPending}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={sendMessageMutation.isPending || !message.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {sendMessageMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            送信
          </button>
        </form>
      </div>
    </div>
  );
}
