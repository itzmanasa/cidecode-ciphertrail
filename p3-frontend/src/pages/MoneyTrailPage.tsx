import { useCase } from "../context/CaseContext";
import { useMoneyTrail } from "../hooks/useMoneyTrail";

export function MoneyTrailPage() {
  const { caseId } = useCase();
  const { data, loading } = useMoneyTrail(caseId ?? undefined);

  if (!caseId) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Money Trail</h1>
        <p className="mt-4">Please select a case first.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-6">
        Loading Money Trail...
      </div>
    );
  }

return (
  <div className="p-6">

    <h1 className="text-3xl font-bold mb-6">
      Money Trail
    </h1>

    {(!data || !data.trail || data.trail.length === 0) && (
      <div className="rounded-lg border p-6 text-center text-gray-500">
        No money trail available.
      </div>
    )}

    {data?.trail?.map((credit: any) => (

      <details
        key={credit.credit_txn_id}
        className="mb-5 rounded-xl border bg-white shadow-sm"
      >

        <summary className="cursor-pointer p-5">

          <div className="flex justify-between">

            <div>

              <p className="text-lg font-bold text-green-700">
                ₹{credit.credit_amount.toLocaleString()}
              </p>

              <p className="text-sm text-gray-500">
                {credit.credit_date}
              </p>

              <p className="text-sm">
                From : <b>{credit.source}</b>
              </p>

            </div>

            <div className="text-right">

              <p className="text-sm text-gray-500">
                Remaining
              </p>

              <p className="font-semibold">
                ₹{credit.remaining_amount.toLocaleString()}
              </p>

            </div>

          </div>

        </summary>

        <div className="border-t bg-gray-50 p-5">

          <h2 className="mb-3 font-semibold">
            Debits consuming this credit
          </h2>

          {credit.debits.length === 0 ? (

            <p className="text-gray-500">
              No debits yet
            </p>

          ) : (

            credit.debits.map((debit: any) => (

              <div
                key={debit.debit_txn_id}
                className="mb-3 rounded-lg border bg-white p-4"
              >

                <div className="flex justify-between">

                  <div>

                    <p className="font-semibold text-red-600">
                      ₹{debit.amount_used.toLocaleString()}
                    </p>

                    <p className="text-sm">
                      To : {debit.destination}
                    </p>

                  </div>

                  <div className="text-sm text-gray-500">
                    {debit.debit_date}
                  </div>

                </div>

              </div>

            ))

          )}

        </div>

      </details>

    ))}

  </div>
);
}