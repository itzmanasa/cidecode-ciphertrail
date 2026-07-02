import { useNavigate } from "react-router-dom";
import { FolderSearch } from "lucide-react";
import { EmptyState } from "../ui/EmptyState";
import { Button } from "../ui/Button";

export function NoActiveCase({ message }: { message?: string }) {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={<FolderSearch className="h-9 w-9" />}
        title="No active case selected"
        description={message || "Upload a statement or open a case from Uploaded Cases to view this page."}
        action={
          <div className="flex gap-2">
            <Button onClick={() => navigate("/upload")}>Upload statement</Button>
            <Button variant="outline" onClick={() => navigate("/cases")}>Browse cases</Button>
          </div>
        }
      />
    </div>
  );
}
