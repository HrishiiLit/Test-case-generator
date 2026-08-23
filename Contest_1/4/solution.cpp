// Input
//     Each test consists of several test cases.The first line contains one integer
//         t(
//                                                 1
// ≤ t
// ≤ 10 4) — the number of test cases.The description of the test cases follows.

//     The first line of each test case contains three integers
//     n
//     ,
//     k
//     ,
//     x(
//         1
// ≤ n,
//         k
// ≤ 10 5;
//         1
// ≤ x
// ≤ 10 18)
//         .

//     The second line of each test case contains
//     n
//     integers
//     a
//     i(
//             1
// ≤ a
//                 i
// ≤ 10 8)
//         .

//     Additional constraints on the input:

// the sum of
//     n
//         across all test cases does not exceed 2
// ⋅ 10 5;
// the sum of
//     k
//         across all test cases does not exceed 2
// ⋅ 10 5
//             .Output
//                 For each test case,
//     output one integer — the number of suitable positions
//         l
//             in the array
//                 b
//                     .

#include <bits/stdc++.h>
    using namespace std;
#define int long long

    void solve(){
        int n, k, x;
        cin >> n >> k >> x;
        vector<int> a(n);
        for (int i = 0; i < n; i++){
            cin >> a[i];}

        if (accumulate(a.begin(), a.end(), 0ll) * k < x){
            cout << 0 << '\n';
            return;}

        int l = 1,
        r = n * k;
        while (l <= r){
            int m = l + (r - l) / 2;
            int cnt_a = (n * k - m + 1) / n;
            int suff = (n * k - m + 1) % n;
            int sum = cnt_a * accumulate(a.begin(), a.end(), 0ll);
            for (int i = n - suff; i < n; i++){
                sum += a[i];} if (sum < x){
                r = m - 1;} else {
                l = m + 1;}}

        cout
        << r << '\n';}

signed main(){
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    cout.tie(0);

    int t;
    cin >> t;
    while (t--){
        solve();}}