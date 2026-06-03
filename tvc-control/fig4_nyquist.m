%% fig4_nyquist.m 
%  Nyquist plot of L(s) woith one open-loop RHP pole (P=1) the Nyquist
%  criterion requires exactly one counter-clockwise encirclement of -1
%  for closed-loop stability (N = -P = -1)

tvc_params;

figure('Color','w','Position',[100 100 480 460]);
nyquist(L); grid on;
title('Nyquist plot of L(s) = C(s)G(s)');
set(findall(gcf,'Type','line'),'LineWidth',1.3);

% zoom in around the critical point 
axis([-3 1 -2 2]);
hold on; plot(-1,0,'r+','MarkerSize',12,'LineWidth',2);
text(-1.05,0.25,'-1','Color','r','FontSize',11);

exportgraphics(gcf,'fig_nyquist.pdf','ContentType','vector');
disp('saved fig_nyquist.pdf');

% print the encirclement check 
P = sum(real(pole(L))>0);
fprintf('Open-loop RHP poles P = %d  =>  need N = -%d encirclement(s) of -1\n',P,P);
