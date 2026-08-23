// Input
// The first line contains n
//  (1≤n≤2⋅105) — number of hours per day.

// The second line contains n
//  integer numbers a1,a2,…,an
//  (0≤ai≤1), where ai=0
//  if the i-th hour in a day is working and ai=1 if the i-th hour is resting. It is guaranteed that ai=0 for at least one i.

// Output
// Print the maximal number of continuous hours during which Polycarp rests. Remember that you should consider that days go one after another endlessly and Polycarp uses the same schedule for each day.


#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }

    int result = 0;
    int len = 0;

    // Traverse twice to simulate circular array
    for (int i = 0; i < 2 * n; i++) {
        if (a[i % n] == 1) {
            len++;
            result = max(result, len);
        } else {
            len = 0;
        }
    }

    cout << result << '\n';
    return 0;
}